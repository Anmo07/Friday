from langchain.tools import tool
import feedparser

@tool("RSS Feed Reader")
def rss_reader_tool(feed_url: str) -> str:
    """
    Reads the latest entries from an RSS feed provided via URL.
    Useful for explicitly validating facts directly from Official/Government primary sources that publish feeds.
    """
    try:
        feed = feedparser.parse(feed_url)
        entries = []
        # Grab top 3 latest items to avoid flooding
        for entry in feed.entries[:3]:
            # Some feeds put desc map into 'summary' or others
            summary_content = entry.get('summary', 'No summary provided')
            entries.append(f"Title: {entry.get('title', 'Unknown')} - Link: {entry.get('link', 'Unknown')} - Summary: {summary_content}")
            
        if not entries:
             # Basic heuristic if the feed is parsed wrong or is empty
             return f"No readable entries found navigating to feed '{feed_url}'."
             
        return " \n".join(entries)
    except Exception as e:
        return f"Failed to parse RSS schema on {feed_url}. Error context: {e}"
