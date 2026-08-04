import os
import asyncio
import aiocoap

target_ip = os.environ.get("TARGET_IP", "127.0.0.1")

async def main():
    protocol = await aiocoap.Context.create_client_context()

    uri = f"coap://{target_ip}/test"
    print(f"Starting CoAP Client testing connection to {uri}")

    while True:
        try:
            request = aiocoap.Message(code=aiocoap.GET, uri=uri)
            response = await protocol.request(request).response
            print(f"Result: {response.code}\nPayload: {response.payload}")
        except Exception as e:
            print(f"Failed to fetch resource: {e}")

        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
