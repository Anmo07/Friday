from langchain.tools import tool


@tool("Search Web Placeholder")
def search_web_tool(query: str) -> str:
    return f"Simulated semantic search and web results for: {query}. Extracted Evidence found: [Dummy Evidence Truth]."
