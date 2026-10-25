
import os 
import asyncio
import certifi 
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

 

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={os.environ['TAVILY_API_KEY']}",
        }
    }
)



async def get_all_tools():
    tools = await client.get_tools()
    print('Available tools on server:- ')
    for tool in tools:
        print(tool.name)


tavily_search_tool = None

async def get_tavily_search_tool():
    global tavily_search_tool

    if tavily_search_tool is not None:
        return tavily_search_tool

    tools = await client.get_tools()

    tavily_search_tool = next(
        (tool for tool in tools if tool.name == "tavily_search"),
        None
    )

    if tavily_search_tool is None:
        raise ValueError("Tavily search tool not found in available MCP tools.")

    return tavily_search_tool



async def tavily_mcp_search(query:str):
     search_tool = await get_tavily_search_tool()

     results = await search_tool.ainvoke(
          {'query' : query}
     )

     return results