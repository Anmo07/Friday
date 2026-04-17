import pytest
import requests
import websockets
import os

BASE_URL = os.getenv("VERITAS_BASE_URL", "http://localhost:8000")
WS_URL = os.getenv("VERITAS_WS_URL", "ws://localhost:8000/ws/stream")

def test_fastapi_health():
    """ Tests if the Docker container is serving FastAPI over port 8000. """
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.fail("Backend Container is effectively down or port is fully exposed gracefully.")

@pytest.mark.asyncio
async def test_websocket_health():
    """ Tests the Event-Driven Engine bounds mappings over WebSocket natively perfectly. """
    try:
        async with websockets.connect(WS_URL) as websocket:
            await websocket.send('{"query": " "}')
            response = await websocket.recv()
            assert '"status": "error"' in response or '"status":"error"' in response
    except Exception as e:
        pytest.fail(f"WebSocket execution crashed aggressively bounding limits: {e}")
