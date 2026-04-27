from langchain.tools import tool
import json
import time

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except Exception:
    feedparser = None
    _FEEDPARSER_AVAILABLE = False


def _debug_log(hypothesis_id: str, message: str, data: dict) -> None:
    # #region agent log
    try:
        with open("/Users/anmol/Downloads/Developer/Friday/.cursor/debug-cf7383.log", "a", encoding="utf-8") as fp:
            fp.write(
                json.dumps(
                    {
                        "sessionId": "cf7383",
                        "runId": "run1",
                        "hypothesisId": hypothesis_id,
                        "location": "tools/rss_reader.py",
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

@tool("RSS Feed Reader")
def rss_reader_tool(feed_url: str) -> str:
    """
    Reads the latest entries from an RSS feed provided via URL.
    Useful for explicitly validating facts directly from Official/Government primary sources that publish feeds.
    """
    # #region agent log
    _debug_log(
        "H2",
        "rss_reader_tool_called",
        {"feedparser_available": _FEEDPARSER_AVAILABLE, "feed_prefix": str(feed_url)[:80]},
    )
    # #endregion
    if not _FEEDPARSER_AVAILABLE:
        # #region agent log
        _debug_log("H2", "feedparser_missing_graceful_degrade", {"feed_prefix": str(feed_url)[:80]})
        # #endregion
        return f"Failed to parse RSS schema on {feed_url}. Error context: feedparser is not installed in this runtime."
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
