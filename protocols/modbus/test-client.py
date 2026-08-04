import os
import time
from pymodbus.client import ModbusTcpClient

target_ip = os.environ.get("TARGET_IP", "127.0.0.1")
framer_type = os.environ.get("MODBUS_FRAMER", "tcp").lower()

print(f"Starting Modbus Client (Framer: {framer_type}) testing connection to {target_ip}:502")

if framer_type == "rtu":
    from pymodbus.framer.rtu_framer import ModbusRtuFramer
    client = ModbusTcpClient(target_ip, port=502, framer=ModbusRtuFramer)
else:
    client = ModbusTcpClient(target_ip, port=502)

while True:
    try:
        if client.connect():
            print(f"Successfully connected to {target_ip}:502")
            result = client.read_holding_registers(1, 1, slave=1)
            if result.isError():
                print(f"Error reading register: {result}")
            else:
                print(f"Read holding register 1: {result.registers[0]}")
            client.close()
        else:
            print(f"Failed to connect to {target_ip}:502")
    except Exception as e:
        print(f"Exception during Modbus polling: {e}")

    time.sleep(5)
