import asyncio
import aiocoap.resource as resource
import aiocoap

class TestResource(resource.Resource):
    async def render_get(self, request):
        return aiocoap.Message(payload=b"Test CoAP Server Data")

    async def render_put(self, request):
        print(f"Received PUT payload: {request.payload}")
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"Payload accepted")

async def main():
    root = resource.Site()
    root.add_resource(['test'], TestResource())

    print("Starting CoAP Server on 0.0.0.0:5683")
    await aiocoap.Context.create_server_context(root)

    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
