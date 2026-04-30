import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, Tuple
import requests
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import HuggingFaceEncoder
from core.vector_client import ChromaClient
from core.graph_client import Neo4jClient
from core.truth_engine import TruthEngine
from core.firewall import HallucinationFirewall

logger = logging.getLogger(__name__)


class FridayPipeline:
    def __init__(self):
        t0 = time.monotonic()
        from core.mcp_manager import mcp_manager

        self.encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")
        self.router = self._build_semantic_router()
        self.vector_db = ChromaClient()
        self.graph_db = Neo4jClient()
        self.truth_engine = TruthEngine()
        self.firewall = HallucinationFirewall()
        self.mcp = mcp_manager
        self.memory = []  # Added for conversation context
        logger.info(f"FridayPipeline initialized in {time.monotonic() - t0:.2f}s")

    def _build_semantic_router(self) -> SemanticRouter:
        fast_route = Route(
            name="tier_1_fast",
            utterances=[
                "open the terminal",
                "what time is it",
                "turn up the volume",
                "create a new folder",
                "system status",
                "show me my files",
                "launch the browser",
                "restart the service",
                "open my downloads folder",
                "list running processes",
                "check disk space",
                "shut down the system",
                "set an alarm",
                "take a screenshot",
                "toggle dark mode",
            ],
        )
        standard_route = Route(
            name="tier_2_standard",
            utterances=[
                "what is the capital of france",
                "summarize this article",
                "who is the CEO of Apple",
                "define quantum mechanics",
                "what happened in the news today",
                "explain photosynthesis",
                "tell me about the history of the internet",
                "what is machine learning",
                "who invented the telephone",
                "what is the GDP of India",
                "explain the theory of relativity",
                "who won the 2024 election",
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
        return SemanticRouter(
            encoder=self.encoder, routes=[fast_route, standard_route, deep_route]
        )

    _DEEP_KEYWORDS = {
        "investigate",
        "cross-reference",
        "verify",
        "fact-check",
        "analyze",
        "corroborate",
        "validate",
        "audit",
        "discrepancies",
        "misinformation",
        "contradictions",
        "SEC",
        "WHO",
        "deep analysis",
    }
    _FAST_KEYWORDS = {
        "open",
        "launch",
        "restart",
        "shut down",
        "toggle",
        "screenshot",
        "alarm",
        "folder",
        "terminal",
        "browser",
        "volume",
        "disk space",
    }

    def classify(self, query: str) -> str:
        route = self.router(query)
        semantic_tier = route.name if route.name else "tier_2_standard"
        return self._boost_tier(query, semantic_tier)

    def _boost_tier(self, query: str, semantic_tier: str) -> str:
        q_lower = query.lower()
        if semantic_tier == "tier_2_standard":
            if any(kw in q_lower for kw in self._DEEP_KEYWORDS):
                return "tier_3_deep"
            if any(kw in q_lower for kw in self._FAST_KEYWORDS):
                return "tier_1_fast"
        return semantic_tier

    async def retrieve_vector(self, query: str) -> Dict[str, Any]:
        return await self.vector_db.asimilarity_search(query)

    async def retrieve_graph(self, query: str) -> Dict[str, Any]:
        return await self.graph_db.aquery_graph(query)

    async def retrieve_parallel(
        self, query: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        vector_res, graph_res = await asyncio.gather(
            self.retrieve_vector(query), self.retrieve_graph(query)
        )
        return vector_res, graph_res

    def reciprocal_rank_fusion(
        self, vector_results: list, graph_results: list, k: int = 60
    ) -> list:
        rrf_scores = {}
        for rank, doc in enumerate(vector_results):
            doc_id = doc.get("id")
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(graph_results):
            doc_id = doc.get("id")
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
        return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    async def run(self, query: str, voice_mode: bool = False) -> Dict[str, Any]:
        tier = self.classify(query)
        if tier == "tier_1_fast":
            if any(kw in query.lower() for kw in self._FAST_KEYWORDS):
                return {"response": await self._run_mcp_agent(query), "tier": tier}
            return {
                "response": await self._run_fast_agent(query, voice_mode=voice_mode),
                "tier": tier,
            }
        elif tier == "tier_2_standard":
            vector_res = await self.retrieve_vector(query)
            return {
                "response": await self._run_standard_agent(
                    query, vector_res, voice_mode=voice_mode
                ),
                "tier": tier,
            }
        else:
            return await self._execute_tier_3(query, voice_mode=voice_mode)

    async def _execute_tier_3(
        self, query: str, voice_mode: bool = False
    ) -> Dict[str, Any]:
        vector_res, graph_res = await self.retrieve_parallel(query)
        fused_context = self.reciprocal_rank_fusion(
            vector_res.get("hits", []), graph_res.get("hits", [])
        )
        reasoning_output = await self._run_reasoning_agent(
            query, fused_context, voice_mode=voice_mode
        )
        truth_data = {
            "sources": ["db", "kg"],
            "vector_similarity": vector_res.get("avg_similarity", 0.0),
            "graph_connectivity": graph_res.get("centrality_score", 0.0),
            "temporal_anomalies": False,
            "fake_probability": 0.05,
        }
        score_report = self.truth_engine.compute_truth_score(truth_data)
        if score_report["truth_score"] < 0.75:
            reasoning_output = await self._run_verification_agent(
                reasoning_output, fused_context
            )
        final_output = self.firewall.validate(reasoning_output, fused_context)
        return {
            "response": final_output,
            "truth_score": score_report["truth_score"],
            "breakdown": score_report.get("breakdown", {}),
            "tier": "tier_3_deep",
            "context_used": fused_context,
        }

    async def stream_run(
        self, query: str, voice_mode: bool = False
    ) -> AsyncGenerator[str, None]:
        tier = self.classify(query)
        from models.ollama_runtime import resolve_model_name

        voice_instructions = ""
        if voice_mode:
            voice_instructions = "SYSTEM: You are Friday. Priority: Brevity. Response must be <20 words. Use conversational prosody (um, well, actually). No markdown. No lists. Maintain a premium, helpful tone.\n"
        if tier == "tier_1_fast":
            prompt = f"{voice_instructions}You are Friday, a fast local OS agent. Execute and confirm.\nQuery: {query}"
            model = (
                resolve_model_name(["llama3.1:8b", "phi3", "mistral"]) or "llama3.1:8b"
            )
            context = None
        elif tier == "tier_2_standard":
            vector_res = await self.retrieve_vector(query)
            context = vector_res
            prompt = f"{voice_instructions}Answer concisely based on context.\nContext: {context}\nQuery: {query}"
            model = (
                resolve_model_name(
                    ["llama3.1:8b-instruct", "llama3.1", "llama3", "mistral"]
                )
                or "llama3.1:8b-instruct"
            )
        else:
            vector_res, graph_res = await self.retrieve_parallel(query)
            fused_context = self.reciprocal_rank_fusion(
                vector_res.get("hits", []), graph_res.get("hits", [])
            )
            context = fused_context
            prompt = f"{voice_instructions}Perform deep reasoning and analysis.\nContext: {context}\nQuery: {query}"
            model = (
                resolve_model_name(
                    ["llama3.1:8b-instruct", "llama3.1", "llama3", "mistral"]
                )
                or "llama3.1:8b-instruct"
            )
        yield self._sse_event("meta", {"tier": tier, "model": model})
        full_response = ""
        async for token in self._stream_ollama(prompt, model):
            full_response += token
            yield self._sse_event("token", {"t": token})
        if tier == "tier_3_deep":
            truth_data = {
                "sources": ["db", "kg"],
                "vector_similarity": vector_res.get("avg_similarity", 0.0),
                "graph_connectivity": graph_res.get("centrality_score", 0.0),
                "temporal_anomalies": False,
                "fake_probability": 0.05,
            }
            score_report = self.truth_engine.compute_truth_score(truth_data)
            yield self._sse_event("truth_score", score_report)
        yield self._sse_event("done", {"response_length": len(full_response)})

    async def _stream_ollama(
        self, prompt: str, model: str
    ) -> AsyncGenerator[str, None]:
        from app.core.config import settings

        def _blocking_stream():
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.0},
            }
            resp = requests.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json=payload,
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break

        queue = asyncio.Queue()

        def _producer():
            try:
                for token in _blocking_stream():
                    queue.put_nowait(token)
            except Exception as e:
                logger.error(f"Ollama stream error: {e}")
            finally:
                queue.put_nowait(None)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _producer)
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token

    @staticmethod
    def _sse_event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def _get_llm(self, preferred_model: str, temperature: float = 0.0):
        from models.ollama_runtime import create_ollama_llm, resolve_model_name

        model = resolve_model_name([preferred_model]) or preferred_model
        return create_ollama_llm(model=model, temperature=temperature)

    async def _run_mcp_agent(self, query: str) -> str:
        llm = self._get_llm("llama3.1:8b", temperature=0.0)
        tools = self.mcp.get_tool_schemas()
        response = await llm.ainvoke(
            f"SYSTEM: You are Friday. Use tools to satisfy the request.\nTOOLS: {json.dumps(tools)}\nQuery: {query}"
        )
        if "{" in response and "name" in response:
            try:
                call_data = json.loads(
                    response[response.find("{") : response.rfind("}") + 1]
                )
                tool_output = await self.mcp.execute_tool(
                    call_data["name"], call_data.get("arguments", {})
                )
                return await llm.ainvoke(f"Tool Result: {tool_output}\nQuery: {query}")
            except:
                return response
        return response

    async def _run_fast_agent(self, query: str, voice_mode: bool = False) -> str:
        instruction = (
            "Respond in one short sentence."
            if voice_mode
            else "Respond in one sentence."
        )
        llm = self._get_llm("phi3:mini", temperature=0.0)
        return await llm.ainvoke(f"You are Friday. {instruction}\nQuery: {query}")

    async def _run_standard_agent(
        self, query: str, context: Any, voice_mode: bool = False
    ) -> str:
        instruction = (
            "Be conversational and brief." if voice_mode else "Answer concisely."
        )
        llm = self._get_llm("llama3.1:8b-instruct", temperature=0.0)
        return await llm.ainvoke(
            f"{instruction} based on context.\nContext: {context}\nQuery: {query}"
        )

    async def _run_reasoning_agent(
        self, query: str, context: Any, voice_mode: bool = False
    ) -> str:
        instruction = (
            "Be conversational and brief." if voice_mode else "Perform deep reasoning."
        )
        llm = self._get_llm("llama3.1:8b-instruct", temperature=0.2)
        return await llm.ainvoke(f"{instruction}\nContext: {context}\nQuery: {query}")

    async def _run_verification_agent(self, draft: str, context: Any) -> str:
        llm = self._get_llm("llama3.1:8b-instruct", temperature=0.0)
        return await llm.ainvoke(
            f"Verify and correct the following draft given the context.\nContext: {context}\nDraft: {draft}"
        )
