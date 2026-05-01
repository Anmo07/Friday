import logging
from typing import Dict, Optional
import asyncio
import socket

logger = logging.getLogger(__name__)

class ServiceRegistry:
    def __init__(self):
        self.services: Dict[str, bool] = {
            "ollama": False,
            "neo4j": False,
            "chromadb": False,
            "redis": False
        }
        self.limited_mode: bool = False

    def is_healthy(self, service_name: str) -> bool:
        return self.services.get(service_name, False)

    async def check_all_services(self):
        """Perform health checks on all registered services."""
        checks = [
            self.check_ollama(),
            self.check_port("neo4j", 7687),
            self.check_chroma(),
            self.check_port("redis", 6379)
        ]
        await asyncio.gather(*checks)
        
        # If Ollama is down, enable Limited Mode (Critical)
        if not self.services["ollama"]:
            self.limited_mode = True
            logger.warning("Ollama is DOWN. Friday will run in CRITICAL LIMITED MODE.")
        else:
            self.limited_mode = False
            # Check for other services just for reporting
            down_services = [s for s, h in self.services.items() if not h and s != "ollama"]
            if down_services:
                logger.info(f"Secondary services ({', '.join(down_services)}) are offline. Using local embedded defaults.")
            else:
                logger.info("All services are healthy.")

    async def check_ollama(self) -> bool:
        try:
            import requests
            from app.core.config import settings
            resp = await asyncio.to_thread(requests.get, f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2)
            self.services["ollama"] = resp.status_code == 200
        except Exception:
            self.services["ollama"] = False
        return self.services["ollama"]

    async def check_chroma(self) -> bool:
        try:
            import chromadb
            # If we can import it, the embedded client will work
            self.services["chromadb"] = True
        except ImportError:
            self.services["chromadb"] = False
        return self.services["chromadb"]

    async def check_port(self, service_name: str, port: int, host: str = "localhost") -> bool:
        try:
            # Simple socket check for port availability
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            self.services[service_name] = (result == 0)
            sock.close()
        except Exception:
            self.services[service_name] = False
        return self.services[service_name]

service_registry = ServiceRegistry()
