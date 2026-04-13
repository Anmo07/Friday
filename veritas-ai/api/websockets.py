from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline
from pipelines.event_bus import event_bus
import asyncio
import json
import logging

router = APIRouter(prefix="/ws")

async def stream_alerts_to_client(websocket: WebSocket):
    """
    Background worker actively listening synchronously on the Event Bus Global Stream.
    Pushes Phase 14 dynamically calculated High Severity anomalies strictly onto the client stream actively.
    """
    async for event in event_bus.subscribe("global_alerts"):
        try:
            await websocket.send_json({
                "status": "alert",
                "data": event["payload"]
            })
        except Exception:
            break

@router.websocket("/stream")
async def websocket_query_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint strictly routing real-time constraints securely over native HTTP suspensions.
    """
    await websocket.accept()
    logging.info("WebSocket connection established resolving structural queries actively.")
    
    # Spawn a concurrent asynchronous listener exclusively attached to global logic drops
    alert_task = asyncio.create_task(stream_alerts_to_client(websocket))
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                query = payload.get("query", "")
            except:
                query = data
                
            if not query.strip():
                await websocket.send_json({"error": "Empty query payload blocked logically."})
                continue
                
            await websocket.send_json({
                "status": "processing", 
                "message": f"Orchestrating autonomous logic streams globally for: {query}"
            })
            
            # Run the streaming topology actively passing control execution into the Producer loop arrays
            try:
                response = await run_multi_agent_pipeline(query)
                
                # Push the deterministic strictly parsed QueryResponse JSON downstream securely
                await websocket.send_json({
                    "status": "complete",
                    "data": response.model_dump()
                })
            except Exception as pipe_err:
                await websocket.send_json({"error": f"Internal Structural Payload Crashed: {pipe_err}"})
            
    except WebSocketDisconnect:
        logging.info("Client successfully cleanly decoupled from intelligence streams.")
    except Exception as e:
        logging.error(f"WebSocket execution mapping crashed fatally: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        # Guarantee closure of background loop logic arrays
        alert_task.cancel()
