import asyncio
import logging
from typing import Dict, Any

class EventBus:
    """
    Asynchronous Message Broker executing Phase 13 logic constraints natively.
    Replaces blocking linear execution by decoupling publishers and subscribers.
    Simulates Kafka/Redis Streams routing topology securely in memory utilizing asyncio maps.
    """
    def __init__(self):
        self.topics: Dict[str, asyncio.Queue] = {}
        # Stores HTTP / WebSocket request resolution hooks explicitly targeting stateless APIs
        self.response_futures: Dict[str, asyncio.Future] = {} 

    def _get_queue(self, topic: str) -> asyncio.Queue:
        if topic not in self.topics:
            self.topics[topic] = asyncio.Queue()
        return self.topics[topic]

    async def publish(self, topic: str, event_type: str, payload: dict):
        logging.info(f"EventBus Emitting -> Stream: '{topic}' | Event: [{event_type}]")
        await self._get_queue(topic).put({"type": event_type, "payload": payload})

    async def subscribe(self, topic: str):
        """
        Yields streamed payloads sequentially acting as the asynchronous consumer layer.
        """
        queue = self._get_queue(topic)
        while True:
            msg = await queue.get()
            yield msg
            queue.task_done()

# Global streaming router
event_bus = EventBus()
