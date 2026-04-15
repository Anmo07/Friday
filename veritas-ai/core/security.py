from datetime import datetime, timedelta
import logging
import os
import secrets
from threading import Lock
from typing import Dict, Optional

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader


API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
_api_key_lock = Lock()


def _default_api_clients() -> Dict[str, dict]:
    dev_key = os.getenv("VERITAS_DEV_API_KEY")
    enterprise_key = os.getenv("VERITAS_ENTERPRISE_API_KEY")

    if not dev_key and not enterprise_key:
        dev_key = f"veritas_dev_{secrets.token_hex(8)}"
        logging.warning(
            "No API keys were configured. Generated an ephemeral local development key. "
            "Set VERITAS_DEV_API_KEY and VERITAS_ENTERPRISE_API_KEY in production."
        )

    clients: Dict[str, dict] = {}
    if dev_key:
        clients[dev_key] = {
            "tier": "free",
            "requests": 0,
            "limit": int(os.getenv("VERITAS_FREE_TIER_LIMIT", "100")),
            "reset_at": datetime.utcnow() + timedelta(hours=1),
            "owner": os.getenv("VERITAS_DEV_API_OWNER", "local-development"),
        }
    if enterprise_key:
        clients[enterprise_key] = {
            "tier": "enterprise",
            "requests": 0,
            "limit": int(os.getenv("VERITAS_ENTERPRISE_LIMIT", "10000")),
            "reset_at": datetime.utcnow() + timedelta(hours=1),
            "owner": os.getenv("VERITAS_ENTERPRISE_OWNER", "enterprise"),
        }
    return clients


DEVELOPER_DB = _default_api_clients()


def validate_api_key(api_key: Optional[str]) -> str:
    """Validate the caller API key and enforce a basic fixed-window rate limit."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide an X-API-KEY header.",
        )

    with _api_key_lock:
        client = DEVELOPER_DB.get(api_key)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid developer API key.",
            )

        if datetime.utcnow() > client["reset_at"]:
            client["requests"] = 0
            client["reset_at"] = datetime.utcnow() + timedelta(hours=1)

        if client["requests"] >= client["limit"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for tier [{client['tier']}].",
            )

        client["requests"] += 1

    return api_key


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    return validate_api_key(api_key)


def generate_new_api_key(tier: str = "free", email: str = "default@veritas.ai") -> str:
    """Generate a new in-memory API key for local administration workflows."""
    new_key = f"veritas_{secrets.token_hex(16)}"
    limit = 10000 if tier == "enterprise" else 100
    with _api_key_lock:
        DEVELOPER_DB[new_key] = {
            "tier": tier,
            "requests": 0,
            "limit": limit,
            "reset_at": datetime.utcnow() + timedelta(hours=1),
            "owner": email,
        }
    return new_key
