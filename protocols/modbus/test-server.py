import os
import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.framer.rtu_framer import ModbusRtuFramer

framer_type = os.environ.get("MODBUS_FRAMER", "tcp").lower()

async def run_server():
    print(f"Starting Modbus Server (Framer: {framer_type}) on 0.0.0.0:502")
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*100),
        co=ModbusSequentialDataBlock(0, [0]*100),
        hr=ModbusSequentialDataBlock(0, [0]*100),
        ir=ModbusSequentialDataBlock(0, [0]*100))

    context = ModbusServerContext(slaves=store, single=True)

    if framer_type == "rtu":
        await StartAsyncTcpServer(context=context, address=("0.0.0.0", 502), framer=ModbusRtuFramer)
    else:
        await StartAsyncTcpServer(context=context, address=("0.0.0.0", 502))

if __name__ == "__main__":
    asyncio.run(run_server())
