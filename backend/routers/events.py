import asyncio
import os
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("live_alerts")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message["data"])
            
            # Check if client disconnected by waiting for 0 seconds for any incoming frame
            try:
                await asyncio.wait_for(websocket.receive(), timeout=0.001)
            except asyncio.TimeoutError:
                pass # Still connected
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        await pubsub.unsubscribe("live_alerts")
        await r.aclose()
