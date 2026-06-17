import asyncio
import websockets

async def test():
    uri = "ws://localhost:8000/api/v1/workspace/build?node_id=n1780913184722&template=rust-std"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            while True:
                msg = await websocket.recv()
                print("Received:", msg)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
