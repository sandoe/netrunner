import asyncio
import os
import random
from asyncua import Server

async def simulate_values(vars_list):
    while True:
        for var in vars_list:
            bname = (await var.read_browse_name()).Name.lower()
            current_val = await var.read_value()

            new_val = current_val
            if "cpu" in bname:
                new_val = round(random.uniform(5.0, 95.0), 2)
            elif "temp" in bname:
                new_val = round(random.uniform(35.0, 85.0), 2)
            elif "ram" in bname or "memory" in bname:
                new_val = random.randint(1024, 16384)
            elif "disk" in bname:
                if isinstance(current_val, (int, float)):
                    new_val = round(current_val + random.uniform(0.0, 0.5), 2)
            else:
                if isinstance(current_val, int):
                    new_val = current_val + random.randint(-2, 2)
                elif isinstance(current_val, float):
                    new_val = round(current_val + random.uniform(-2.0, 2.0), 2)

            await var.write_value(new_val)

        await asyncio.sleep(2)

async def run_server():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Test OPC-UA Server")

    uri = "http://netrunner.local"
    idx = await server.register_namespace(uri)

    node = await server.nodes.objects.add_object(idx, "TestObject")

    tags_env = os.environ.get("OPC_TAGS", "")
    created_vars = []

    if tags_env:
        tags = [t.strip() for t in tags_env.split(",")]
        for tag in tags:
            if "=" in tag:
                name, val = tag.split("=", 1)
                try:
                    if "." in val:
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    pass
                var = await node.add_variable(idx, name, val)
            else:
                var = await node.add_variable(idx, tag, 0.0)
            await var.set_writable()
            created_vars.append(var)
    else:
        var = await node.add_variable(idx, "TestVariable", 42.0)
        await var.set_writable()
        created_vars.append(var)

    print("Starting OPC-UA Server on 0.0.0.0:4840")
    async with server:
        asyncio.create_task(simulate_values(created_vars))
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_server())
