import asyncio
import logging
from typing import AsyncGenerator

from app.core.assistant import assistant_orchestrator
from core.personality import friday_personality
from models.multi_llm import get_fast_llm

logger = logging.getLogger(__name__)

class ConversationLayer:
    """Intelligent conversational layer that runs BEFORE all agents.
    Handles fast casual chats instantly and routes deep queries to the main pipeline.
    """
    
    def __init__(self):
        self.memory = []
        self.fast_llm = None
        self.stop_event = asyncio.Event()

    async def initialize(self):
        self.fast_llm = get_fast_llm()

    def add_memory(self, role: str, content: str):
        """Track last 3 messages (6 interactions max)"""
        self.memory.append({"role": role, "content": content})
        if len(self.memory) > 6:
            self.memory = self.memory[-6:]

    def _format_prompt(self, query: str) -> str:
        prompt = friday_personality.get_system_prompt() + "\n\n"
        for m in self.memory:
            role = "Boss" if m["role"] == "user" else "FRIDAY"
            prompt += f"{role}: {m['content']}\n"
        prompt += f"Boss: {query}\nFRIDAY:"
        return prompt

    async def process_query_stream(self, query: str) -> AsyncGenerator[str, None]:
        self.stop_event.clear()
        
        # Phase 5: Interrupt
        if friday_personality.detect_interruption(query):
            yield friday_personality.stopping_response() + "\n"
            return
            
        self.add_memory("user", query)
        intent = assistant_orchestrator.classify(query)
        
        # Phase 1 & 3: Casual/Simple -> Instant LLM response (Skip Pipeline)
        if intent.kind == "chat":
            prompt = self._format_prompt(query)
            full_response = ""
            
            try:
                # LLM stream for fast conversational response
                for chunk in self.fast_llm.stream(prompt):
                    if self.stop_event.is_set():
                        break
                    yield chunk
                    full_response += chunk
                    await asyncio.sleep(0.01)
                
                # Save to memory
                self.add_memory("assistant", full_response.strip())
                
            except Exception as e:
                logger.error(f"Fast LLM stream failed: {e}")
                yield f"[Error: {e}]"
            return

        # Phase 1: Deep Analysis / Verification -> Main Pipeline
        yield f"{intent.opening_line}\n"
        
        try:
            response = await assistant_orchestrator.execute(query, deep_requested=intent.deep)
            summary = response.get("summary", "Done, Boss.")
            yield summary
            self.add_memory("assistant", summary)
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            yield f"\n[Pipeline Error: {e}]"
        
    def interrupt(self):
        """Halt immediately"""
        self.stop_event.set()
