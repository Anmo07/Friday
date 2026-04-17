from langchain.tools import tool
import json
from memory.knowledge_graph import AsyncKnowledgeGraph

@tool("Knowledge Graph Entity Builder")
async def kg_build_tool(data_json: str) -> str:
    """
    Inserts autonomously extracted entities and relationships mapping directly into the structural Knowledge Graph.
    Input MUST strictly follow JSON structure:
    {
       "entities": [{"label": "Person|Organization|Event|Location", "name": "NAME"}],
       "relationships": [{"subject": "SUBJ_NAME", "subject_label": "LABEL", "rel": "ANNOUNCED|OCCURRED_AT|AFFILIATED_WITH|REPORTED_BY", "obj": "OBJ_NAME", "obj_label": "LABEL"}]
    }
    """
    try:
        data = json.loads(data_json)
        kg = AsyncKnowledgeGraph()
        await kg.connect()
        
        # Phase 10: Batch processing for entities
        entities = [(ent["label"], ent["name"]) for ent in data.get("entities", [])]
        await kg.batch_merge_entities(entities)
            
        for rel in data.get("relationships", []):
            await kg.merge_relationship(
                rel["subject"], 
                rel["subject_label"], 
                rel["rel"], 
                rel["obj"], 
                rel["obj_label"]
            )
            
        return "Knowledge Graph memory explicitly updated with structural tensors."
    except json.JSONDecodeError:
        return "Error: Payload failed JSON strict parsing limits."
    except Exception as e:
        return f"Failed to ingest logic relationships: {e}"

@tool("Knowledge Graph Validator")
async def kg_validate_tool(entity_name: str) -> str:
    """
    Queries the Knowledge Graph dynamically to retrieve all structural truths relating explicitly to a Node Entity.
    Input should be directly a singular entity string representation (e.g. "WHO", "Washington D.C.").
    Returns string relationships mapping.
    """
    kg = AsyncKnowledgeGraph()
    await kg.connect()
    res = await kg.query_relationships(entity_name)
    return res
