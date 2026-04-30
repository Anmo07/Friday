import asyncio
from typing import Optional, List, Tuple

from neo4j.async_driver import AsyncGraphDatabase, AsyncDriver
from config.settings import settings
import logging

ALLOWED_LABELS = {"Person", "Organization", "Event", "Location"}
ALLOWED_RELATIONSHIPS = {"ANNOUNCED", "OCCURRED_AT", "AFFILIATED_WITH", "REPORTED_BY"}


class AsyncKnowledgeGraph:
    """
    Async Entity-Relationship Knowledge Graph with connection pooling.
    """

    _instance: Optional["AsyncKnowledgeGraph"] = None
    _driver: Optional[AsyncDriver] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=30,
                )
                await self._driver.verify_connectivity()
                logging.info("Async Neo4j connection established")
            except Exception as e:
                logging.error(f"Could not connect to Neo4j: {e}")
                self._driver = None

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def merge_entity(self, label: str, name: str) -> None:
        if not self._driver:
            return
        if label not in ALLOWED_LABELS:
            logging.warning("Rejected unsupported Neo4j label: %s", label)
            return

        query = f"MERGE (n:{label} {{name: $name}})"
        try:
            async with self._driver.session() as session:
                await session.run(query, name=name)
        except Exception as e:
            logging.error(f"Failed to merge entity {name}: {e}")

    async def merge_relationship(
        self, subject: str, subject_label: str, rel: str, obj: str, obj_label: str
    ) -> None:
        if not self._driver:
            return
        if (
            subject_label not in ALLOWED_LABELS
            or obj_label not in ALLOWED_LABELS
            or rel not in ALLOWED_RELATIONSHIPS
        ):
            logging.warning(
                "Rejected unsupported graph relationship: %s -[%s]-> %s",
                subject_label,
                rel,
                obj_label,
            )
            return

        query = (
            f"MATCH (s:{subject_label} {{name: $subject}}) "
            f"MATCH (o:{obj_label} {{name: $obj}}) "
            f"MERGE (s)-[:{rel}]->(o)"
        )
        try:
            async with self._driver.session() as session:
                await session.run(query, subject=subject, obj=obj)
        except Exception as e:
            logging.error(f"Failed to merge relation: {e}")

    async def query_relationships(self, entity_name: str) -> str:
        if not self._driver:
            return "Neo4j Offline - Cannot fetch strict relation checks."

        query = (
            "MATCH (n {name: $name})-[r]->(m) "
            "RETURN labels(n)[0] AS n_lbl, type(r) AS rel, labels(m)[0] AS m_lbl, m.name AS m_name "
            "LIMIT 10"
        )
        results_str = []
        try:
            async with self._driver.session() as session:
                result = await session.run(query, name=entity_name)
                records = await result.data()
                for record in records:
                    results_str.append(
                        f"({record['n_lbl']}: {entity_name}) -[{record['rel']}]-> "
                        f"({record['m_lbl']}: {record['m_name']})"
                    )
        except Exception as e:
            logging.error(f"Failed fetching relations for {entity_name}: {e}")

        if results_str:
            return " | ".join(results_str)
        return f"No explicitly mapped relationships found for {entity_name}"

    async def batch_merge_entities(self, entities: List[Tuple[str, str]]) -> None:
        if not self._driver or not entities:
            return

        async def _merge_batch(batch: List[Tuple[str, str]]):
            async with self._driver.session() as session:
                for label, name in batch:
                    if label in ALLOWED_LABELS:
                        await session.run(
                            f"MERGE (n:{label} {{name: $name}})", name=name
                        )

        batch_size = 50
        tasks = [
            _merge_batch(entities[i : i + batch_size])
            for i in range(0, len(entities), batch_size)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


class KnowledgeGraph:
    """
    Sync wrapper for backward compatibility.
    """

    def __init__(self):
        self._async_kg = AsyncKnowledgeGraph()
        self.driver = None

    def close(self):
        pass

    def merge_entity(self, label: str, name: str) -> None:
        asyncio.create_task(self._async_kg.merge_entity(label, name))

    def merge_relationship(
        self, subject: str, subject_label: str, rel: str, obj: str, obj_label: str
    ) -> None:
        asyncio.create_task(
            self._async_kg.merge_relationship(
                subject, subject_label, rel, obj, obj_label
            )
        )

    def query_relationships(self, entity_name: str) -> str:
        return ""
