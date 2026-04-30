import asyncio
import numpy as np
from typing import Dict, Any, Tuple
from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder

# Simulated imports for Vector and Graph clients
from core.vector_client import ChromaClient
from core.graph_client import Neo4jClient
from core.truth_engine import TruthEngine
from core.firewall import HallucinationFirewall

class AntigravityPipeline:
    def __init__(self):
        self.encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2") # local embedding model
        self.router = self._build_semantic_router()
        self.vector_db = ChromaClient()
        self.graph_db = Neo4jClient()
        self.truth_engine = TruthEngine()
        self.firewall = HallucinationFirewall()

    def _build_semantic_router(self) -> RouteLayer:
        fast_route = Route(
            name="tier_1_fast",
            utterances=[
                "open the terminal", "what time is it", "turn up the volume",
                "create a new folder", "system status", "show me my files",
                "launch the browser", "restart the service", "open my downloads folder",
                "list running processes", "check disk space", "shut down the system",
                "set an alarm", "take a screenshot", "toggle dark mode",
            ],
        )
        standard_route = Route(
            name="tier_2_standard",
            utterances=[
                "what is the capital of france", "summarize this article",
                "who is the CEO of Apple", "define quantum mechanics",
                "what happened in the news today", "explain photosynthesis",
                "tell me about the history of the internet", "what is machine learning",
                "who invented the telephone", "what is the GDP of India",
                "explain the theory of relativity", "who won the 2024 election",
            ],
        )
        deep_route = Route(
            name="tier_3_deep",
            utterances=[
                "investigate the discrepancies in the Q3 financial report",
                "cross-reference these two research papers on mRNA vaccines",
                "analyze the geopolitical impact of the new trade agreement",
                "verify if the claims in this article are factually correct",
                "fact-check this news story against multiple sources",
                "analyze and verify the claims in the WHO pandemic report",
                "cross-reference this financial statement against SEC filings",
                "investigate supply chain disruption patterns in Q4 earnings",
                "deep analysis of misinformation trends in social media",
                "verify the accuracy of this scientific paper's conclusions",
            ],
        )
        return RouteLayer(
            encoder=self.encoder,
            routes=[fast_route, standard_route, deep_route],
        )

    async def retrieve_vector(self, query: str) -> Dict[str, Any]:
        """Fetch from ChromaDB asynchronously"""
        return await self.vector_db.asimilarity_search(query)

    async def retrieve_graph(self, query: str) -> Dict[str, Any]:
        """Fetch from Neo4j asynchronously"""
        return await self.graph_db.aquery_graph(query)

    def reciprocal_rank_fusion(self, vector_results: list, graph_results: list, k: int = 60) -> list:
        """Fuses Vector and Graph results using RRF"""
        rrf_scores = {}
        for rank, doc in enumerate(vector_results):
            doc_id = doc.get('id')
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
            
        for rank, doc in enumerate(graph_results):
            doc_id = doc.get('id')
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
            
        # Sort and return top fused results
        return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    async def execute_tier_3(self, query: str) -> Dict[str, Any]:
        """Deep Execution: Async Hybrid RAG + State-based Agent Workflow"""
        # 1. Parallel Retrieval (Asynchronous Hybrid RAG)
        vector_task = asyncio.create_task(self.retrieve_vector(query))
        graph_task = asyncio.create_task(self.retrieve_graph(query))
        
        vector_res, graph_res = await asyncio.gather(vector_task, graph_task)
        
        # 2. Reciprocal Rank Fusion Synthesis
        fused_context = self.reciprocal_rank_fusion(vector_res.get('hits', []), graph_res.get('hits', []))
        
        # 3. First Agent Pass
        reasoning_output = await self._run_reasoning_agent(query, fused_context)
        
        # 4. Truth Engine Scoring
        truth_data = {
            "sources": ["db", "kg"],
            "vector_similarity": vector_res.get("avg_similarity", 0.0),
            "graph_connectivity": graph_res.get("centrality_score", 0.0),
            "temporal_anomalies": False,
            "fake_probability": 0.05
        }
        score_report = self.truth_engine.compute_truth_score(truth_data)
        
        # 5. State-based Conditional Handoff
        if score_report["truth_score"] < 0.75:
            # Only trigger secondary agent if confidence is low
            reasoning_output = await self._run_verification_agent(reasoning_output, fused_context)
            
        # 6. Pre-output Hallucination Firewall
        final_output = self.firewall.validate(reasoning_output, fused_context)
        
        return {
            "response": final_output,
            "truth_score": score_report["truth_score"],
            "context_used": fused_context
        }

    # Keyword signals that override the semantic router for borderline queries
    _DEEP_KEYWORDS = {
        "investigate", "cross-reference", "verify", "fact-check", "analyze",
        "corroborate", "validate", "audit", "discrepancies", "misinformation",
        "contradictions", "SEC", "WHO", "deep analysis",
    }
    _FAST_KEYWORDS = {
        "open", "launch", "restart", "shut down", "toggle", "screenshot",
        "alarm", "folder", "terminal", "browser", "volume", "disk space",
    }

    def _boost_tier(self, query: str, semantic_tier: str) -> str:
        """Keyword fallback: override semantic tier for borderline queries."""
        q_lower = query.lower()

        # If semantic says standard, check if keywords suggest deep or fast
        if semantic_tier == "tier_2_standard":
            if any(kw in q_lower for kw in self._DEEP_KEYWORDS):
                return "tier_3_deep"
            if any(kw in q_lower for kw in self._FAST_KEYWORDS):
                return "tier_1_fast"

        return semantic_tier

    async def run(self, query: str) -> Dict[str, Any]:
        """Entry point - MoE Gate with keyword-boosted fallback."""
        route = self.router(query)
        semantic_tier = route.name if route.name else "tier_2_standard"
        tier = self._boost_tier(query, semantic_tier)

        if tier == "tier_1_fast":
            return {"response": await self._run_fast_agent(query), "tier": tier}
        elif tier == "tier_2_standard":
            vector_res = await self.retrieve_vector(query)
            return {"response": await self._run_standard_agent(query, vector_res), "tier": tier}
        else:
            return await self.execute_tier_3(query)

    # Agent execution — uses Ollama local models per MoE tier config
    def _get_llm(self, preferred_model: str, temperature: float = 0.0):
        """Get an OllamaLLM, falling back to whatever model is installed."""
        from models.ollama_runtime import create_ollama_llm, resolve_model_name
        model = resolve_model_name([preferred_model]) or preferred_model
        return create_ollama_llm(model=model, temperature=temperature)

    async def _run_fast_agent(self, query: str) -> str:
        llm = self._get_llm("phi3:mini", temperature=0.0)
        return await llm.ainvoke(
            f"You are a fast local OS agent. Respond in one sentence.\nQuery: {query}"
        )

    async def _run_standard_agent(self, query: str, context: Any) -> str:
        llm = self._get_llm("llama3:8b", temperature=0.0)
        return await llm.ainvoke(
            f"Answer concisely based on context.\nContext: {context}\nQuery: {query}"
        )

    async def _run_reasoning_agent(self, query: str, context: Any) -> str:
        llm = self._get_llm("mixtral:8x7b", temperature=0.2)
        return await llm.ainvoke(
            f"Perform deep reasoning and analysis.\nContext: {context}\nQuery: {query}"
        )

    async def _run_verification_agent(self, draft: str, context: Any) -> str:
        llm = self._get_llm("llama3:8b", temperature=0.0)
        return await llm.ainvoke(
            f"Verify and correct the following draft given the context.\nContext: {context}\nDraft: {draft}"
        )
