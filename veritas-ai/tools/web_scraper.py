from langchain.tools import tool
from playwright.sync_api import sync_playwright

@tool("Web Content Scraper Tool")
def web_scrape_tool(url: str) -> str:
    """
    Scrapes the main text content from a provided URL using Playwright.
    Useful for reading article contents directly or extracting official statements.
    """
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
                
            browser.close()
            # Normalize and trim to prevent breaking LLM context windows (5k char slice is safe typically)
            cleaned_text = ' '.join(text.split())
            return cleaned_text[:5000] 
    except Exception as e:
        return f"Failed to scrape {url}. Error: {e}"
