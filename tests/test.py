
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv()

# from mcp_client_test import load_tools ,tavily_mcp_search ,get_all_tools

# from mcp_client_test import get_all_tools
from mcp_cleint import get_all_tools

if __name__ == "__main__":
    asyncio.run(get_all_tools())
