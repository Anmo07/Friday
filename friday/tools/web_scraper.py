from langchain.tools import tool
import json
import time

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    sync_playwright = None
    _PLAYWRIGHT_AVAILABLE = False


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
                        "location": "tools/web_scraper.py",
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

@tool("Web Content Scraper Tool")
def web_scrape_tool(url: str) -> str:
    """
    Scrapes the main text content from a provided URL using Playwright.
    Useful for reading article contents directly or extracting official statements.
    """
    browser = None
    # #region agent log
    _debug_log(
        "H2",
        "web_scrape_tool_called",
        {"playwright_available": _PLAYWRIGHT_AVAILABLE, "url_prefix": str(url)[:80]},
    )
    # #endregion
    if not _PLAYWRIGHT_AVAILABLE:
        # #region agent log
        _debug_log("H2", "playwright_missing_graceful_degrade", {"url_prefix": str(url)[:80]})
        # #endregion
        return f"Failed to scrape {url}. Error: playwright is not installed in this runtime."
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            # Simple heuristic sequence to extract main document text over standard tags
            if page.locator("article").count() > 0:
                text = page.locator("article").first.inner_text()
            elif page.locator("main").count() > 0:
                text = page.locator("main").first.inner_text()
            else:
                text = page.locator("body").inner_text()
                
            cleaned_text = ' '.join(text.split())
            return cleaned_text[:5000] 
    except Exception as e:
        return f"Failed to scrape {url}. Error: {e}"
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
