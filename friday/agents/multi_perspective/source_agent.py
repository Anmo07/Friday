import asyncio
from typing import List, Dict, Any
from tools.news_api import news_search_tool
from tools.web_scraper import web_scrape_tool
from tools.rss_reader import rss_reader_tool

class SourceAgent:
    def __init__(self):
        self.name = "Source Agent"

    async def run(self, query: str) -> Dict[str, Any]:
        """
        Fetches raw data from news APIs, web scraping, and RSS feeds in parallel.
        """
        print(f"[{self.name}] Gathering data for: {query}")
        
        tasks = [
            asyncio.to_thread(news_search_tool, query),
            asyncio.to_thread(rss_reader_tool, query),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # results[0] is news, results[1] is rss
        news_data = results[0]
        rss_data = results[1]
        
        # For simplicity in Phase 1, we just return the strings
        return {
            "query": query,
            "news_results": news_data,
            "rss_results": rss_data,
            "timestamp": asyncio.get_event_loop().time()
        }
