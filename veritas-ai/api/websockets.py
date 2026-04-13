from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline
import json
import logging

router = APIRouter(prefix="/ws")

@router.websocket("/stream")
async def websocket_query_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time querying.
    Allows persistent connections and asynchronous intelligence streams natively decoupled from HTTP timeouts.
    """
    await websocket.accept()
    logging.info("WebSocket connection established.")
    try:
        while True:
            # Receive query payload dynamically
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                query = payload.get("query", "")
            except:
                query = data
                
            if not query.strip():
                await websocket.send_json({"error": "Empty query payload."})
                continue
                
            # Stream status acknowledgment 
            await websocket.send_json({
                "status": "processing", 
                "message": f"Orchestrating autonomous agents for query mapping: {query}"
            })
            
            # Execute Phase 6 Pipeline completely isolated within the Socket context
            try:
                response = await run_multi_agent_pipeline(query)
                
                # Push the deterministic strictly parsed QueryResponse JSON downstream
                await websocket.send_json({
                    "status": "complete",
                    "data": response.model_dump()
                })
            except Exception as pipe_err:
                await websocket.send_json({"error": f"Internal Pipeline Execution Error: {pipe_err}"})
            
    except WebSocketDisconnect:
        logging.info("Client cleanly disconnected from intelligent websocket stream.")
    except Exception as e:
        logging.error(f"WebSocket unhandled structural error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
