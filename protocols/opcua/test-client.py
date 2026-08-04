import os
import asyncio
from asyncua import Client

target_ip = os.environ.get("TARGET_IP", "127.0.0.1")
url = f"opc.tcp://{target_ip}:4840/freeopcua/server/"
tags_env = os.environ.get("OPC_TAGS", "")

async def run_client():
    print(f"Starting OPC-UA Client testing connection to {url}")
    tags_to_read = [t.strip() for t in tags_env.split(",")] if tags_env else []

    while True:
        try:
            async with Client(url=url) as client:
                print(f"Connected to {url}")
                root = client.nodes.root
                print(f"Root node is: {root}")

                if tags_to_read:
                    uri = "http://netrunner.local"
                    try:
                        idx = await client.get_namespace_index(uri)
                        obj = await client.nodes.objects.get_child(f"{idx}:TestObject")
                        for tag in tags_to_read:
                            tag_name = tag.split("=")[0] if "=" in tag else tag
                            var = await obj.get_child(f"{idx}:{tag_name}")
                            val = await var.read_value()
                            print(f"Read tag '{tag_name}': {val}")
                    except Exception as e:
                        print(f"Could not read custom tags: {e}")
                else:
                    print("No OPC_TAGS provided. Skipping tag reads.")

        except Exception as e:
            print(f"Failed to connect to {url}: {e}")

        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_client())
