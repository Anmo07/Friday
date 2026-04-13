from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime, timedelta
import secrets

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Simulated Database of active explicitly mapped Developer Platform Keys
DEVELOPER_DB = {
    "veritas_test_key_123": {
        "tier": "free", 
        "requests": 0, 
        "limit": 100, 
        "reset_at": datetime.now() + timedelta(hours=1),
        "owner": "test_developer@veritas.ai"
    },
    "veritas_enterprise_456": {
        "tier": "enterprise", 
        "requests": 0, 
        "limit": 10000, 
        "reset_at": datetime.now() + timedelta(hours=1),
        "owner": "corp@partner.com"
    }
}

async def get_api_key(api_key: str = Security(api_key_header)):
    """ Interceptor natively authenticating explicitly routed Developer API actions structurally. """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="API Key explicitly missing. Provide 'X-API-KEY' header."
        )
    
    if api_key not in DEVELOPER_DB:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid or highly revoked Developer API Key"
        )
        
    client = DEVELOPER_DB[api_key]
    
    # Mathematical Rate Limiting Logic seamlessly engaged
    if datetime.now() > client["reset_at"]:
        client["requests"] = 0
        client["reset_at"] = datetime.now() + timedelta(hours=1)
        
    if client["requests"] >= client["limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail=f"Rate limit strictly exceeded for tier [{client['tier']}]."
        )
        
    # Usage Tracking mathematically mapping limits implicitly
    client["requests"] += 1
    
    return api_key

def generate_new_api_key(tier="free", email="default@veritas.ai"):
    """ Natively generates new keys structurally. """
    new_key = f"veritas_{secrets.token_hex(16)}"
    limit = 10000 if tier == "enterprise" else 100
    DEVELOPER_DB[new_key] = {
        "tier": tier,
        "requests": 0,
        "limit": limit,
        "reset_at": datetime.now() + timedelta(hours=1),
        "owner": email
    }
    return new_key
