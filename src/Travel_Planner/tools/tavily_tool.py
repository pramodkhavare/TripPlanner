import os
import time
from typing import List, Optional
from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()
_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])



def _tavily_search(query: str, max_results: int = 5) -> List[dict]:  

    resp = None 
    try:
        resp = _tavily.search(
            query=query,
            max_results=max_results
        )                          # success -> stop retrying
    except Exception as e:
        print(f"[warn] Tavily attempt failed for {query!r}: {e}") 

    if resp is None:                          # all attempts failed
        return []

    normalized: List[dict] = []
    for r in resp.get("results", []):
        title = r.get('title' ,'unknown')
        url = (r.get("url") or "").strip()
        snippet = (r.get("content") or "").strip()
        if not url or not snippet:
            continue

        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ",1)[0] + "..."
        normalized.append({
            "title": r.get("title") or "",
            "url": url,
            "snippet": snippet,  ##content 
        })
    return "\n\n".join(
    f"{r['title']}\n{r['url']}\n{r['snippet']}" for r in normalized
)