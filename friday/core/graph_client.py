"""Neo4j async graph client for the Antigravity Pipeline."""

import asyncio
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async wrapper around Neo4j for knowledge-graph queries."""

    def __init__(self):
        self._driver = None

    def _get_driver(self):
        """Lazy-load the Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                user = os.getenv("NEO4J_USER", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "password")
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
            except Exception as e:
                logger.warning(f"Neo4j init failed: {e}")
        return self._driver

    async def aquery_graph(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Run a graph query asynchronously via thread offload."""
        return await asyncio.to_thread(self._query_graph_sync, query, limit)

    def _query_graph_sync(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Synchronous Cypher query against Neo4j."""
        driver = self._get_driver()
        if driver is None:
            logger.info("Neo4j unavailable — returning empty results")
            return {"hits": [], "centrality_score": 0.0}

        try:
            with driver.session() as session:
                # Full-text search for entities related to the query
                cypher = (
                    "CALL db.index.fulltext.queryNodes('entity_index', $search_text) "
                    "YIELD node, score "
                    "RETURN node.id AS id, node.text AS text, score "
                    "LIMIT $limit"
                )
                result = session.run(cypher, search_text=query, limit=limit)
                hits = []
                scores = []
                for record in result:
                    hits.append({
                        "id": record["id"],
                        "text": record["text"],
                        "score": record["score"],
                    })
                    scores.append(record["score"])

                centrality = sum(scores) / len(scores) if scores else 0.0
                return {"hits": hits, "centrality_score": round(min(centrality, 1.0), 4)}

        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")
            return {"hits": [], "centrality_score": 0.0}

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._driver = None
