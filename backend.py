import os 
import certifi
from dotenv import load_dotenv
from typing import TypedDict ,Annotated ,List
import uuid
import operator
import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph ,START ,END
from langgraph.checkpoint.postgres import PostgresSaver


from langchain.messages import HumanMessage ,ToolMessage ,AIMessage ,SystemMessage
from langchain_core.messages import AnyMessage
from langchain_groq import ChatGroq
from src.Travel_Planner.tools import tavily_tool ,flight_tool


load_dotenv()




def get_database_url():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is missing from .env")

    separator = "&" if "?" in url else "?"
    if "sslmode=" not in url:
        url = f"{url}{separator}sslmode=require"

    return url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        'GROQ api key is not available in env varible check and add'
    )


#####LLM
# llm = ChatGroq(
#     api_key=GROQ_API_KEY ,
#     model="qwen/qwen3.8-27b"
# )


llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="qwen/qwen3.8-27b",
    temperature=0.3,
    max_tokens=900,   # must stay under the 1000 OTPM limit
)

###STATE:-

class TravelState(TypedDict):
    messages : Annotated[List[AnyMessage] ,operator.add]
    user_query :  str 
    flight_results :str 
    hotel_results : str 
    itinerary : str 
    final_response: str
    llm_calls : int 





def flight_node(state:TravelState)->dict:
    query = state['user_query']
    flight_results = flight_tool.search_flights(query=query )

    return {
        "flight_results" : flight_results ,
        "messages" : [
            AIMessage(content="Flight results are fetched")
        ],
        "llm_calls" : state.get('llm_calls' ,0) +1
    }



def hotel_node(state:TravelState) ->dict:
    query = state['user_query']
    hotel_results = tavily_tool._tavily_search(query=query)


    return {
            "hotel_results" : hotel_results ,
            "messages" : [
                AIMessage(content="Best hotels are fetched are fetched")
            ],
            "llm_calls" : state.get('llm_calls' ,0) +1
        }
    



from langchain.messages import HumanMessage, SystemMessage

def itinerary_node(state: TravelState) -> dict:
    prompt = f"""
You are an expert travel planner. Build a practical itinerary
using the following information.

User query: {state['user_query']}

Flight results:
{state['flight_results']}

Hotel results:
{state['hotel_results']}

Create a practical, budget-aware itinerary that is easy to follow.

Include:
- Day-wise schedule
- Flight details and travel time, if available
- Hotel details and check-in information, if available
- Attractions and suggested activities
- Estimated costs, based on available data
- Local transportation suggestions
- Practical tips

Do not invent flight prices, hotel prices, or booking details
that are not present in the provided data.
"""

    itinerary_results = llm.invoke([
        SystemMessage(
            content="You are an expert travel planner."
        ),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": itinerary_results.content,
        "messages": [itinerary_results],
        "llm_calls": state.get("llm_calls", 0) + 1
    }




def final_node(state: TravelState) -> dict:
    prompt = f"""
You are an expert travel planning assistant.
Create a complete, practical final travel plan using the information below.

User query:
{state['user_query']}

Flight results:
{state['flight_results']}

Hotel suggestions:
{state['hotel_results']}

Generated itinerary:
{state['itinerary']}

Format the final answer using these sections:

1. Trip Summary
   - Destination, duration, and travel preferences

2. Flight Information
   - Available flight details
   - Prices and timings, if provided

3. Hotel Suggestions
   - Hotel names, locations, prices, and amenities, if available

4. Day-to-Day Itinerary
   - Daily activities, attractions, and transportation suggestions

5. Estimated Budget
   - Flights, accommodation, food, transport, and activities
   - Clearly distinguish confirmed prices from estimates

6. Final Recommendations
   - Booking tips, local travel advice, and practical reminders

Important instructions:
- Be clear, practical, and easy to follow.
- Do not invent flight availability, hotel details, or prices.
- Live flight APIs may not provide ticket prices. Explicitly mention
  when pricing information is unavailable.
- If information is missing, state that clearly.
- Make budget estimates only when sufficient information is available.
"""

    final_response_results = llm.invoke([
        SystemMessage(
            content="You are a professional AI travel planning assistant."
        ),
        HumanMessage(content=prompt)
    ])

    return {
        "final_response": final_response_results.content,
        "messages": [final_response_results],
        "llm_calls": state.get("llm_calls", 0) + 1
    }





###GRAPh

graph = StateGraph(state_schema=TravelState)

graph.add_node('flight_node' ,flight_node)
graph.add_node('hotel_node' ,hotel_node)
graph.add_node('itinerary_node' ,itinerary_node)
graph.add_node('final_node' ,final_node)

graph.add_edge(START ,'flight_node')
graph.add_edge('flight_node' ,'hotel_node')
graph.add_edge('hotel_node' ,'itinerary_node')
graph.add_edge('itinerary_node' ,'final_node')
graph.add_edge('final_node' ,END)





##Postgree checkpointer 

DATBASE_URL = get_database_url()

_conn = psycopg.connect(
    DATBASE_URL ,
    autocommit=True ,
    row_factory=dict_row
)


checkpointer = PostgresSaver(conn=_conn)
checkpointer.setup()


workflow = graph.compile(checkpointer=checkpointer)





##FINAL caling function

def run_travel_agent(user_input:str ,thread_id : str | None=None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        'configurable' : {
            'thread_id' : thread_id
        }
    }



    input = {
            "messages" : [
                HumanMessage(content=user_input)
            ] ,
            "user_query" :  user_input ,
            "flight_results" : "" ,
            "hotel_results" : "" ,
            "itinerary" : "" ,
            "final_response" : "",
            "llm_calls" : 0 
    }

    # results = workflow.invoke(input=input ,config=config)[-1].content
    final_state = workflow.invoke(input, config=config)
    answer = final_state["messages"][-1].content

    return {
        'thread_id' : thread_id,
        "answer" : answer ,
        "flight_results" : final_state.get('flight_results' ,""),
        "hotel_results" : final_state.get('hotel_results' ,"") ,
        "itinerary" : final_state.get('itinerary' ,"") ,
        "llm_calls" : final_state.get('llm_calls' ,"") 

    }

