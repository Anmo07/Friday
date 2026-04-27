import asyncio
from typing import Dict, Any
from .source_agent import SourceAgent
from .fact_agent import FactAgent
from .perspective_agent import PerspectiveAgent
from .summary_agent import SummaryAgent
from models.schemas import QueryResponse

class MultiPerspectiveOrchestrator:
    def __init__(self):
        self.source_agent = SourceAgent()
        self.fact_agent = FactAgent()
        self.perspective_agent = PerspectiveAgent()
        self.summary_agent = SummaryAgent()

    async def run(self, query: str) -> QueryResponse:
        """
        Runs the multi-agent system:
        Source -> (Fact, Perspective) -> Summary
        """
        # Step 1: Source Agent
        source_data = await self.source_agent.run(query)
        
        # Step 2: Fact and Perspective Agents in parallel
        # Note: PerspectiveAgent might benefit from FactAgent results, 
        # but for maximum parallelism we can run them concurrently if designed so.
        # Here we'll pass source_data to both.
        
        fact_task = asyncio.create_task(self.fact_agent.run(source_data))
        perspective_task = asyncio.create_task(self.perspective_agent.run(query, source_data))
        
        fact_data, perspective_data = await asyncio.gather(fact_task, perspective_task)
        
        # Step 3: Summary Agent
        results = {
            "source_data": source_data,
            "fact_data": fact_data,
            "perspective_data": perspective_data
        }
        
        return await self.summary_agent.run(query, results)
