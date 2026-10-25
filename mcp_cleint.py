
import os 
import asyncio
import certifi 
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

 

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
AVIATION_API_KEY = os.getenv('AVIATION_API_KEY')



client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={os.environ['TAVILY_API_KEY']}",
        } ,
        "aviationstack": {
            "transport": "stdio",
            "command": "uvx",
            "args": [
                  "aviationstack-mcp"
            ],
            "env": {
                  "AVIATION_STACK_API_KEY": AVIATION_API_KEY
            }
        }
    }
)



async def get_all_tools():
    tools = await client.get_tools()
    print('Available tools on server:- ')
    for tool in tools:
        print(tool.name)



##TAVILY AND AVAITION TOOL

search_tool = None
avaition_tool = []


async def initialize_mcp():
    global search_tool
    global avaition_tool

    if search_tool is not None:
        return search_tool, avaition_tool

    tools = await client.get_tools()

    search_tool = next(
        (tool for tool in tools if tool.name == "tavily_search"),
        None
    )

    avaition_tool = [
        tool
        for tool in tools
        if tool.name != "tavily_search"
    ]

    if search_tool is None:
        raise ValueError(
            f"Tavily search tool not found. Available tools: {[t.name for t in tools]}"
        )

    return search_tool, avaition_tool




async def tavily_mcp_search(query:str):
    await initialize_mcp()

    results = await search_tool.ainvoke(
          {'query' : query}
     )

    return results

async def avialtion_mcp_call(
    tool_name: str,
    tool_args: dict = None
):
    await initialize_mcp()   # loads tools once, then reuses them

    tool = next(
        (t for t in avaition_tool if t.name == tool_name),
        None
    )

    if tool is None:
        raise ValueError(
            f"Tool '{tool_name}' not found. Available: {[t.name for t in avaition_tool]}"
        )

    result = await tool.ainvoke(tool_args or {})
    return result




