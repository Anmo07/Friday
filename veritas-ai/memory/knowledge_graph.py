from neo4j import GraphDatabase
from config.settings import settings
import logging

class KnowledgeGraph:
    """
    Manages the Entity-Relationship Knowledge Graph resolving explicit Truth bindings.
    Designed to interface sequentially with Neo4j.
    """
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        except Exception as e:
            logging.error(f"Could not connect to Neo4j instance: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def merge_entity(self, label: str, name: str) -> None:
        """
        Merges explicitly classified entity nodes cleanly.
        Constraints: Person, Organization, Event, Location
        """
        if not self.driver: return
        query = f"MERGE (n:{label} {{name: $name}})"
        with self.driver.session() as session:
            try:
                session.run(query, name=name)
            except Exception as e:
                logging.error(f"Failed to merge entity {name} into Graph: {e}")

    def merge_relationship(self, subject: str, subject_label: str, rel: str, obj: str, obj_label: str) -> None:
        """
        Binds relationships rigidly to stop hallucination looping natively.
        Constraints: ANNOUNCED, OCCURRED_AT, AFFILIATED_WITH, REPORTED_BY
        """
        if not self.driver: return
        query = (
            f"MATCH (s:{subject_label} {{name: $subject}}) "
            f"MATCH (o:{obj_label} {{name: $obj}}) "
            f"MERGE (s)-[:{rel}]->(o)"
        )
        with self.driver.session() as session:
            try:
                session.run(query, subject=subject, obj=obj)
            except Exception as e:
                logging.error(f"Failed to merge relation {subject} -> {rel} -> {obj}: {e}")

    def query_relationships(self, entity_name: str) -> str:
        """
        Fetches full neighboring node boundaries mapping Truth assertions explicitly.
        """
        if not self.driver: return "Neo4j Offline - Cannot fetch strict relation checks."
        query = (
            "MATCH (n {name: $name})-[r]->(m) "
            "RETURN labels(n)[0] AS n_lbl, type(r) AS rel, labels(m)[0] AS m_lbl, m.name AS m_name "
            "LIMIT 10" # Cap traversal arrays
        )
        results_str = []
        with self.driver.session() as session:
            try:
                results = session.run(query, name=entity_name)
                for record in results:
                    results_str.append(f"({record['n_lbl']}: {entity_name}) -[{record['rel']}]-> ({record['m_lbl']}: {record['m_name']})")
            except Exception as e:
                logging.error(f"Failed fetching relations for {entity_name}: {e}")
                
        return " | ".join(results_str) if results_str else f"No explicitly mapped relationships found overriding {entity_name} claims locally."
