import asyncio
import logging
from contextlib import suppress
from typing import Dict, Set

class EventBus:
    """
    Asynchronous Message Broker executing Phase 13 logic constraints natively.
    Replaces blocking linear execution by decoupling publishers and subscribers.
    Simulates Kafka/Redis Streams routing topology securely in memory utilizing asyncio maps.
    """
    def __init__(self):
        self.topics: Dict[str, Set[asyncio.Queue]] = {}
        self.response_futures: Dict[str, asyncio.Future] = {}

    def _register_subscriber(self, topic: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        if topic not in self.topics:
            self.topics[topic] = set()
        self.topics[topic].add(queue)
        return queue

    def _unregister_subscriber(self, topic: str, queue: asyncio.Queue) -> None:
        subscribers = self.topics.get(topic)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self.topics.pop(topic, None)

    async def publish(self, topic: str, event_type: str, payload: dict):
        logging.info(f"EventBus Emitting -> Stream: '{topic}' | Event: [{event_type}]")
        message = {"type": event_type, "payload": payload}
        for queue in list(self.topics.get(topic, set())):
            await queue.put(message)

    async def subscribe(self, topic: str):
        """
        Yields streamed payloads sequentially acting as the asynchronous consumer layer.
        """
        queue = self._register_subscriber(topic)
        try:
            while True:
                msg = await queue.get()
                try:
                    yield msg
                finally:
                    queue.task_done()
        finally:
            self._unregister_subscriber(topic, queue)

    async def fail_response(self, session_id: str, exc: Exception) -> None:
        future = self.response_futures.get(session_id)
        if future and not future.done():
            future.set_exception(exc)

    async def resolve_response(self, session_id: str, payload) -> None:
        future = self.response_futures.get(session_id)
        if future and not future.done():
            future.set_result(payload)

    async def shutdown(self) -> None:
        for future in list(self.response_futures.values()):
            if future.done():
                continue
            future.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.shield(future)
        self.response_futures.clear()
        self.topics.clear()

# Global streaming router
event_bus = EventBus()
