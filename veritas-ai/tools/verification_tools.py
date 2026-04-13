from langchain.tools import tool
from urllib.parse import urlparse
from pipelines.retrieval_pipeline import retrieve_relevant_context_with_scores

@tool("Domain Credibility Evaluator")
def domain_credibility_tool(url: str) -> str:
    """
    Evaluates the credibility of a URL source based on domain authority heuristics.
    Returns a score from 0.0 to 1.0 and categorized domain type ('official', 'media', 'social', 'unknown').
    """
    try:
        domain = urlparse(url).netloc.lower()
        if not domain:
            return "Invalid URL - Score: 0.1 - Type: unknown"
            
        # Basic heuristic logic for source validation mappings
        official_tlds = ['.gov', '.edu', '.mil', '.int']
        reliable_media = ['reuters.com', 'apnews.com', 'bbc.com', 'npr.org', 'bloomberg.com']
        social_media = ['twitter.com', 'x.com', 'facebook.com', 'reddit.com', 'tiktok.com', 'instagram.com']
        
        if any(domain.endswith(tld) for tld in official_tlds):
            return f"Domain: {domain} | Credibility Score: 0.95 | Type: official"
            
        if any(m in domain for m in reliable_media):
            return f"Domain: {domain} | Credibility Score: 0.85 | Type: media"
            
        if any(s in domain for s in social_media):
            return f"Domain: {domain} | Credibility Score: 0.30 | Type: social"
            
        # Baseline internet mapping
        return f"Domain: {domain} | Credibility Score: 0.50 | Type: media"
    except Exception as e:
        return f"Error evaluating URL {url}: {e}"

@tool("RAG Fact Checker")
def rag_fact_check_tool(claim: str) -> str:
    """
    Checks a specific factual claim against the internal Vector Database (RAG).
    Returns factual contradictions or supportive contexts based on embedded history.
    """
    # Fetch top 3 closest historical claims from our Chroma local DB
    results = retrieve_relevant_context_with_scores(claim, top_k=3)
    if not results:
        return f"No prior historical context found in vector DB regarding claim: '{claim}'"
        
    compiled_evidence = []
    for doc, score in results:
        # Distance mapping: Usually < 1.0 indicates high relevance in normalized distances
        compiled_evidence.append(f"[Distance: {score:.2f}]: {doc.page_content}")
        
    return " \n".join(compiled_evidence)
