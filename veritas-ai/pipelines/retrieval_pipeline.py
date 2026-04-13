from typing import List, Tuple
from langchain_core.documents import Document
from memory.vector_store import get_vector_store

def retrieve_relevant_context(query: str, top_k: int = 5) -> List[Document]:
    """
    Perform a semantic search to retrieve the most relevant documents for a given query.
    Used by basic RAG setups.
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
    docs = retriever.invoke(query)
    return docs

def retrieve_relevant_context_with_scores(query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
    """
    Retrieve documents along with their similarity scores.
    Helpful for fact checking or establishing source credibility.
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=top_k)
    return results
