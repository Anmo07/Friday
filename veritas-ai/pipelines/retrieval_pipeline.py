import asyncio
import hashlib
import time
from typing import List, Tuple, Optional, Dict, Any
from langchain_core.documents import Document

from config.settings import settings
from core.redis_cache import vector_cache
from memory.vector_store import get_vector_store, get_embeddings


_vector_store_cache: Optional[Any] = None
_embedding_cache: Optional[Any] = None


def get_cached_vector_store() -> Any:
    global _vector_store_cache
    if _vector_store_cache is None:
        _vector_store_cache = get_vector_store()
    return _vector_store_cache


def get_cached_embeddings() -> Any:
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = get_embeddings()
    return _embedding_cache


def retrieve_relevant_context(
    query: str, top_k: Optional[int] = None
) -> List[Document]:
    top_k = top_k or settings.RETRIEVAL_K
    vector_store = get_cached_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
    docs = retriever.invoke(query)
    return docs


def retrieve_relevant_context_with_scores(
    query: str, top_k: Optional[int] = None
) -> List[Tuple[Document, float]]:
    top_k = top_k or settings.RETRIEVAL_K
    vector_store = get_cached_vector_store()
    results = vector_store.similarity_search_with_score(query, k=top_k)
    return results


async def retrieve_relevant_context_async(
    query: str, top_k: Optional[int] = None, use_cache: bool = True
) -> List[Document]:
    top_k = top_k or settings.RETRIEVAL_K

    if use_cache:
        cached = await vector_cache.get_cached_results(query)
        if cached:
            return [
                Document(
                    page_content=item["content"], metadata=item.get("metadata", {})
                )
                for item in cached
            ]

    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, retrieve_relevant_context, query, top_k)

    if use_cache and docs:
        cache_data = [
            {"content": doc.page_content, "metadata": doc.metadata} for doc in docs
        ]
        await vector_cache.cache_results(query, cache_data, ttl=1800)

    return docs


async def retrieve_with_filtering(
    query: str,
    filter_metadata: Optional[Dict[str, Any]] = None,
    top_k: Optional[int] = None,
) -> List[Document]:
    top_k = top_k or settings.RETRIEVAL_K
    vector_store = get_cached_vector_store()

    if filter_metadata:
        retriever = vector_store.as_retriever(
            search_kwargs={"k": top_k, "filter": filter_metadata}
        )
    else:
        retriever = vector_store.as_retriever(search_kwargs={"k": top_k})

    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, retriever.invoke, query)
    return docs


def compute_query_hash(query: str) -> str:
    normalized = " ".join(query.lower().strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


async def batch_retrieve(
    queries: List[str], top_k: Optional[int] = None
) -> Dict[str, List[Document]]:
    top_k = top_k or settings.RETRIEVAL_K

    tasks = [retrieve_relevant_context_async(q, top_k) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        query: result if not isinstance(result, Exception) else []
        for query, result in zip(queries, results)
    }
