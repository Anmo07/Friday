import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ChromaClient:
    def __init__(self, collection_name: str = "veritas_docs"):
        self.collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            try:
                import chromadb

                client = chromadb.PersistentClient(path="./chroma_db")
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.warning(f"ChromaDB init failed: {e}")
        return self._collection

    async def asimilarity_search(
        self, query: str, n_results: int = 5
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self._similarity_search_sync, query, n_results)

    def _similarity_search_sync(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        collection = self._get_collection()
        if collection is None:
            logger.info("ChromaDB unavailable — returning empty results")
            return {"hits": [], "avg_similarity": 0.0}
        try:
            results = collection.query(query_texts=[query], n_results=n_results)
            hits = []
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            for i, doc_id in enumerate(ids):
                hits.append(
                    {
                        "id": doc_id,
                        "text": documents[i] if i < len(documents) else "",
                        "similarity": 1.0 - distances[i] if i < len(distances) else 0.0,
                    }
                )
            avg_sim = sum(h["similarity"] for h in hits) / len(hits) if hits else 0.0
            return {"hits": hits, "avg_similarity": round(avg_sim, 4)}
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return {"hits": [], "avg_similarity": 0.0}
