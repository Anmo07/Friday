from langchain.tools import tool
import json
from core.truth_engine import TruthEngine


@tool("Truth Scoring Engine")
def truth_scoring_tool(data_json: str) -> str:
    try:
        data = json.loads(data_json)
        engine = TruthEngine()
        result = engine.compute_truth_score(data)
        return json.dumps(result, indent=2)
    except json.JSONDecodeError:
        return "Error: Input must be a valid JSON string mapping exactly to the structural parameters required."
    except Exception as e:
        return f"Truth Engine computation fatally crashed: {e}"
