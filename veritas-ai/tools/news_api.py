from langchain.tools import tool
import requests
from config.settings import settings

@tool("News Search API")
def news_search_tool(query: str) -> str:
    """
    Searches recent news articles based on a query using current events APIs.
    Returns article titles, descriptions, and source URLs. 
    Use this to identify events.
    """
    if not settings.NEWS_API_KEY and not settings.GNEWS_API_KEY:
        # Fallback simulation if you do not define .env files to preserve continuity natively
        return f"Simulated actual NewsAPI results for '{query}'. " \
               f"Article 1: Extensive coverage of {query} across networks [https://example.com/1]. " \
               f"Article 2: Fact-checks debate the legitimacy of claims regarding {query} [https://example.com/2]."
               
    if settings.GNEWS_API_KEY:
        try:
            url = f"https://gnews.io/api/v4/search?q={query}&lang=en&max=4&apikey={settings.GNEWS_API_KEY}"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            results = " \n".join([f"[{a['title']}]({a['url']}): {a['description']}" for a in data.get('articles', [])])
            return results if results else f"No news found for {query}."
        except Exception as e:
             return f"Error fetching news from GNews: {e}"
    
    return "API keys not fully mapped in request, returning empty search."
