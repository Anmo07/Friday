from langchain.tools import tool
import requests
from config.settings import settings


def _format_articles(articles: list) -> str:
    results = []
    for article in articles[:4]:
        title = article.get("title") or "Untitled"
        url = article.get("url") or ""
        description = article.get("description") or "No description provided."
        if not url:
            continue
        results.append(f"[{title}]({url}): {description}")
    return " \n".join(results)


@tool("News Search API")
def news_search_tool(query: str) -> str:
    """
    Searches recent news articles based on a query using current events APIs.
    Returns article titles, descriptions, and source URLs. 
    Use this to identify events.
    """
    if settings.GNEWS_API_KEY:
        try:
            url = f"https://gnews.io/api/v4/search?q={query}&lang=en&max=4&apikey={settings.GNEWS_API_KEY}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            results = _format_articles(data.get('articles', []))
            return results if results else f"No news found for {query}."
        except Exception as e:
            return f"Error fetching news from GNews: {e}"

    if settings.NEWS_API_KEY:
        try:
            url = f"https://newsapi.org/v2/everything?q={query}&language=en&pageSize=4"
            resp = requests.get(url, headers={"X-Api-Key": settings.NEWS_API_KEY}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            results = _format_articles(data.get("articles", []))
            return results if results else f"No news found for {query}."
        except Exception as e:
            return f"Error fetching news from NewsAPI: {e}"

    return "No configured news providers are available for this environment."
