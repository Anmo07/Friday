import pytest
import requests
import asyncio
import websockets

def test_fastapi_health():
    """ Tests if the Docker container is serving FastAPI over port 8000. """
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        # Note: In FastAPI, /docs maps natively safely returning 200 explicitly
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.fail("Backend Container is effectively down or port is fully exposed gracefully.")

@pytest.mark.asyncio
async def test_websocket_health():
    """ Tests the Event-Driven Engine bounds mappings over WebSocket natively perfectly. """
    uri = "ws://localhost:8000/ws/stream"
    try:
        async with websockets.connect(uri) as websocket:
            # Empty stream gracefully triggers logic rejection securely
            await websocket.send('{"query": " "}')
            response = await websocket.recv()
            assert "error" in response
    except Exception as e:
        pytest.fail(f"WebSocket execution crashed aggressively bounding limits: {e}")
