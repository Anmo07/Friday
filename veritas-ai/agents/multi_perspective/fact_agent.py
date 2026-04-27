import asyncio
from typing import List, Dict, Any
from tools.verification_tools import rag_fact_check_tool, domain_credibility_tool
from tools.truth_tools import truth_scoring_tool

class FactAgent:
    def __init__(self):
        self.name = "Fact Agent"

    async def run(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates claims using trusted sources and tools.
        """
        query = source_data.get("query", "")
        print(f"[{self.name}] Validating facts for: {query}")
        
        tasks = [
            asyncio.to_thread(rag_fact_check_tool, query),
            asyncio.to_thread(domain_credibility_tool, query),
            asyncio.to_thread(truth_scoring_tool, query)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            "fact_check_results": results[0],
            "credibility_report": results[1],
            "truth_score_data": results[2],
            "status": "validated"
        }
