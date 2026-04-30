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
    try:
        with open(
            "/Users/anmol/Downloads/Developer/Friday/.cursor/debug-cf7383.log",
            "a",
            encoding="utf-8",
        ) as fp:
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


@tool("RSS Feed Reader")
def rss_reader_tool(feed_url: str) -> str:
    _debug_log(
        "H2",
        "rss_reader_tool_called",
        {
            "feedparser_available": _FEEDPARSER_AVAILABLE,
            "feed_prefix": str(feed_url)[:80],
        },
    )
    if not _FEEDPARSER_AVAILABLE:
        _debug_log(
            "H2",
            "feedparser_missing_graceful_degrade",
            {"feed_prefix": str(feed_url)[:80]},
        )
        return f"Failed to parse RSS schema on {feed_url}. Error context: feedparser is not installed in this runtime."
    try:
        feed = feedparser.parse(feed_url)
        entries = []
        for entry in feed.entries[:3]:
            summary_content = entry.get("summary", "No summary provided")
            entries.append(
                f"Title: {entry.get('title', 'Unknown')} - Link: {entry.get('link', 'Unknown')} - Summary: {summary_content}"
            )
        if not entries:
            return f"No readable entries found navigating to feed '{feed_url}'."
        return " \n".join(entries)
    except Exception as e:
        return f"Failed to parse RSS schema on {feed_url}. Error context: {e}"
