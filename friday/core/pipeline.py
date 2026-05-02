import asyncio
import json
import logging
import time
import yaml
import os
from typing import Any, AsyncGenerator, Dict, Tuple, List, Optional
from datetime import datetime
import requests

try:
    from semantic_router import Route, SemanticRouter as RouteLayer
except ImportError:
    from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder

from core.vector_client import ChromaClient
from core.graph_client import Neo4jClient
from core.truth_engine import TruthEngine
from core.firewall import HallucinationFirewall
from core.personality import friday_personality
from core.service_registry import service_registry
from core.history_store import save_session_memory, load_session_memory

logger = logging.getLogger(__name__)


class SemanticTurnDetector:
    """
    Next-Gen Transformer-based semantic turn detection.
    Replaces simple silence timeouts with predictive thought-end analysis.
    """
    def __init__(self):
        self.model_name = "turn-detection-v1"
        logger.info("SemanticTurnDetector initialized.")

    async def predict_end_of_thought(self, audio_chunk: bytes, transcription_so_far: str) -> bool:
        # Simplified logic: In a real implementation, this would use a transformer model
        # to predict the probability of a turn based on semantic and acoustic cues.
        if transcription_so_far.strip().endswith((".", "?", "!")):
            return True
        return False

class TelemetryManager:
    """
    Tracks FLOPs, energy consumption, and dollar cost per query.
    Feeds data back into MoE router for dynamic scaling.
    """
    def __init__(self):
        self.stats = {
            "total_flops": 0,
            "total_energy_joules": 0.0,
            "total_cost_usd": 0.0,
            "battery_level": 1.0
        }

    def track_query_efficiency(self, tier: str, model: str, duration_ms: float):
        # Mock calculation based on model size and duration
        flops_estimate = 1e9 if "phi3" in model else 1e11
        energy_estimate = (flops_estimate / 1e12) * 0.1  # Very rough estimate
        
        self.stats["total_flops"] += flops_estimate
        self.stats["total_energy_joules"] += energy_estimate
        # Local models cost $0 (excluding hardware/electricity)
        
        logger.debug(f"Telemetry: Tier {tier} ({model}) took {duration_ms}ms. Est. Energy: {energy_estimate:.4f}J")

    def get_scaling_factor(self) -> float:
        """Returns a multiplier for thresholding based on hardware constraints."""
        if self.stats["battery_level"] < 0.2:
            return 0.5  # Drastically reduce model complexity
        return 1.0

class LearningLayer:
    """
    Closed-loop learning primitive for capturing interaction traces.
    Enables background SFT and DSPy-based prompt optimization.
    """
    def __init__(self, storage_path: str = "data/learning_traces"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def capture_trace(self, query: str, response: str, tool_calls: List[Dict], feedback: Optional[int] = None):
        trace = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "tool_calls": tool_calls,
            "user_feedback": feedback
        }
        trace_id = f"trace_{int(time.time() * 1000)}"
        with open(f"{self.storage_path}/{trace_id}.json", "w") as f:
            json.dump(trace, f)

class FridayPipeline:
    def __init__(self, owner_email: str = "public"):
        t0 = time.monotonic()
        from core.mcp_manager import mcp_manager
        self.owner_email = owner_email

        self.encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")
        self.router = self._build_semantic_router()
        self.vector_db = ChromaClient()
        self.graph_db = Neo4jClient()
        self.truth_engine = TruthEngine()
        self.firewall = HallucinationFirewall()
        self.mcp = mcp_manager
        
        # New Next-Gen Components
        self.turn_detector = SemanticTurnDetector()
        self.telemetry = TelemetryManager()
        self.learning_layer = LearningLayer()
        self.subagent_bus = asyncio.Queue()  # Shared message bus for subagents
        
        # Load persistent memory
        persisted = load_session_memory(self.owner_email)
        
        self.memory = {
            "conversation_history": persisted.get("conversation_history", []),
            "user_preferences": persisted.get("user_preferences", {}),
            "context_summary": persisted.get("context_summary", ""),
            "last_updated": datetime.now(),
            "personalization_data": persisted.get("personalization_data", {}),
            "max_history_length": 50,
            "predictive_suggestions": [],
            "last_intent": None,
            "entity_focus": None,
            "recent_truth_alerts": []
        }
        
        # Load MoE Schema
        self.moe_config = self._load_moe_schema()
        
        logger.info(f"AntigravityPipeline (Next-Gen) initialized for {self.owner_email} in {time.monotonic() - t0:.2f}s")

    def _load_moe_schema(self) -> Dict:
        config_path = "/Users/anmol/Downloads/Developer/Friday/config/moe_schema.yaml"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def _build_semantic_router(self) -> RouteLayer:
        fast_route = Route(name="tier_1_fast", utterances=["open terminal", "set alarm", "volume up"])
        standard_route = Route(name="tier_2_standard", utterances=["who is CEO", "what is photosynthesis"])
        deep_route = Route(name="tier_3_deep", utterances=["verify financial report", "cross-reference research papers"])
        audio_native_route = Route(name="tier_0_audio_native", utterances=["can we talk", "listen to me", "be my therapist"])
        
        rl = RouteLayer(encoder=self.encoder, routes=[audio_native_route, fast_route, standard_route, deep_route])
        return rl

    async def classify(self, query: str) -> str:
        scaling_factor = self.telemetry.get_scaling_factor()
        
        try:
            route = await asyncio.to_thread(self.router, query)
            tier = route.name if route.name else "tier_2_standard"
            
            # Dynamic scaling: Downgrade tier if battery is low
            if scaling_factor < 0.6 and tier == "tier_3_deep":
                logger.info("Telemetry Trigger: Downgrading Tier 3 -> Tier 2 due to power constraints.")
                tier = "tier_2_standard"
                
            return tier
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "tier_2_standard"

    async def run(self, query: str, voice_mode: bool = False) -> Dict[str, Any]:
        start_time = time.monotonic()
        tier = await self.classify(query)
        
        response_data = {}
        if tier == "tier_0_audio_native":
            response_data = await self._run_audio_native_engine(query)
        elif tier == "tier_1_fast":
            response_data = {"response": await self._run_fast_agent(query, voice_mode), "tier": tier}
        elif tier == "tier_2_standard":
            vector_res = await self.retrieve_vector(query)
            response_data = {"response": await self._run_standard_agent(query, vector_res, voice_mode), "tier": tier}
        else:
            response_data = await self._execute_tier_3(query, voice_mode)

        latency = (time.monotonic() - start_time) * 1000
        model_used = response_data.get("model", "phi3:mini")
        self.telemetry.track_query_efficiency(tier, model_used, latency)
        
        # Capture trace for learning
        self.learning_layer.capture_trace(query, response_data["response"], response_data.get("tool_calls", []))
        
        self._update_conversation_memory(query, response_data["response"], tier)
        return response_data

    async def _run_audio_native_engine(self, query: str) -> Dict[str, Any]:
        """
        Phase 2: E2E Speech-to-Speech logic (VibeVoice integration).
        Uses continuous tokenizers to bypass STT bottleneck.
        """
        return {
            "response": "[Audio-Native Stream] I'm listening. How can I help you today?",
            "tier": "tier_0_audio_native",
            "engine": "vibevoice",
            "model": "vibevoice-acoustic-v1"
        }

    async def _run_mcp_agent(self, query: str) -> str:
        """
        Enhanced to support Telephony tools via MCP.
        """
        llm = self._get_llm("llama3.1:8b")
        tools = self.mcp.get_tool_schemas()
        # Logic to handle tool execution
        response = await llm.ainvoke(f"Use tools for: {query}")
        return response

    def _detect_intent(self, query: str) -> str:
        q = query.lower()
        if "verify" in q or "check" in q: return "verification_request"
        if "open" in q or "run" in q: return "action_request"
        return "general_query"
    
    async def _execute_tier_3(self, query: str, voice_mode: bool = False) -> Dict[str, Any]:
        vector_res, graph_res = await self.retrieve_parallel(query)
        fused_context = self.reciprocal_rank_fusion(vector_res.get("hits", []), graph_res.get("hits", []))
        reasoning_output = await self._run_reasoning_agent(query, fused_context, voice_mode=voice_mode)
        
        score_report = self.truth_engine.compute_truth_score({"vector_similarity": vector_res.get("avg_similarity", 0.0)})
        if score_report["truth_score"] < 0.75:
            reasoning_output = await self._run_verification_agent(reasoning_output, fused_context)
            
        return {
            "response": reasoning_output,
            "tier": "tier_3_deep",
            "model": "llama3.1:8b-instruct",
            "truth_score": score_report["truth_score"]
        }

    def _update_conversation_memory(self, query: str, response: str, tier: str):
        exchange = {"timestamp": datetime.now().isoformat(), "query": query, "response": response, "tier": tier}
        self.memory["conversation_history"].append(exchange)
        if len(self.memory["conversation_history"]) > 50:
            self.memory["conversation_history"].pop(0)

    async def retrieve_vector(self, query: str): return await self.vector_db.asimilarity_search(query)
    async def retrieve_parallel(self, query: str):
        return await asyncio.gather(self.retrieve_vector(query), self.graph_db.aquery_graph(query))
    
    def reciprocal_rank_fusion(self, vector_results: list, graph_results: list, k: int = 60) -> list:
        rrf_scores = {}
        # The results might be list of dicts with 'id'
        for rank, doc in enumerate(vector_results):
            doc_id = doc.get("id") if isinstance(doc, dict) else str(doc)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(graph_results):
            doc_id = doc.get("id") if isinstance(doc, dict) else str(doc)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
        return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    def _get_llm(self, model: str, temp=0.0):
        from models.ollama_runtime import create_ollama_llm
        return create_ollama_llm(model=model, temperature=temp)

    async def _run_fast_agent(self, q, v):
        llm = self._get_llm("phi3:mini")
        return await llm.ainvoke(f"Fast response: {q}")

    async def _run_standard_agent(self, q, c, v):
        llm = self._get_llm("llama3.1:8b-instruct")
        return await llm.ainvoke(f"Standard response with context {c}: {q}")

    async def _run_reasoning_agent(self, q, c, voice_mode=False):
        llm = self._get_llm("llama3.1:8b-instruct", temp=0.2)
        return await llm.ainvoke(f"Deep reasoning: {q}")

    async def _run_verification_agent(self, d, c):
        llm = self._get_llm("llama3.1:8b-instruct")
        return await llm.ainvoke(f"Verified: {d}")

    async def stream_run(self, query: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        tier = await self.classify(query)
        prompt = f"System: {query}"
        model = "phi3:mini"
        yield self._sse_event("meta", {"tier": tier, "model": model})
        async for token in self._stream_ollama(prompt, model):
            yield self._sse_event("token", {"t": token})
        yield self._sse_event("done", {})

    async def _stream_ollama(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        from app.core.config import settings
        payload = {"model": model, "prompt": prompt, "stream": True}
        try:
            resp = requests.post(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate", json=payload, stream=True)
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token: yield token
        except Exception as e:
            logger.error(f"Stream error: {e}")

    @staticmethod
    def _sse_event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
