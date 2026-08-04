import asyncio
import logging
from typing import Dict, Any
import time

logger = logging.getLogger("bluetooth")

# Global dict to store discovered devices
# Format: MAC_ADDRESS -> { "name": str, "rssi": int, "last_seen": float, "mac": str }
discovered_devices: Dict[str, Dict[str, Any]] = {}
bluetooth_queue = asyncio.Queue()

from typing import Optional
_scanner_task: Optional[asyncio.Task] = None


async def bluetooth_scanner_loop():
    """Continuously scans for BLE devices and updates the global dictionary."""
    try:
        from bleak import BleakScanner
    except ImportError:
        logger.error("bleak not installed. Bluetooth scanner disabled.")
        return

    logger.info("Starting Bluetooth BLE scanner...")

    def detection_callback(device, advertisement_data):
        now = time.time()
        mac = device.address

        # Determine name: either from advertisement data or device name
        name = advertisement_data.local_name or device.name or "Unknown Device"
        rssi = advertisement_data.rssi

        # Parse Manufacturer Data
        mf_data = {}
        for company_id, data_bytes in advertisement_data.manufacturer_data.items():
            mf_data[company_id] = data_bytes.hex()

        prev = discovered_devices.get(mac)
        should_emit = False

        if not prev:
            should_emit = True
            discovered_devices[mac] = {
                "mac": mac,
                "name": name,
                "rssi": rssi,
                "last_seen": now,
                "manufacturer_data": mf_data,
                "service_uuids": advertisement_data.service_uuids,
                "tx_power": advertisement_data.tx_power,
                "nodes": {"SERVER": {"rssi": rssi, "last_seen": now}},
            }
        else:
            # Update existing safely to preserve fields like azimuth
            prev["last_seen"] = now
            if mf_data:
                prev["manufacturer_data"] = mf_data
            if advertisement_data.service_uuids:
                prev["service_uuids"] = advertisement_data.service_uuids
            if advertisement_data.tx_power is not None:
                prev["tx_power"] = advertisement_data.tx_power

            # Update name if we found a better one
            if (
                prev.get("name", "Unknown Device") == "Unknown Device"
                and name != "Unknown Device"
            ):
                prev["name"] = name
                should_emit = True

            # Update nodes
            if "nodes" not in prev:
                prev["nodes"] = {}
            prev["nodes"]["SERVER"] = {"rssi": rssi, "last_seen": now}

            # Recalculate top RSSI for simple views
            best_rssi = -1000
            for n_id, n_data in prev["nodes"].items():
                if n_data["rssi"] > best_rssi and now - n_data["last_seen"] < 60:
                    best_rssi = n_data["rssi"]

            old_rssi = prev.get("rssi", -1000)
            prev["rssi"] = best_rssi

            if abs(old_rssi - best_rssi) > 5:
                should_emit = True

        if should_emit:
            try:
                bluetooth_queue.put_nowait(
                    {"type": "device_update", "device": discovered_devices[mac]}
                )
            except Exception:
                pass

    try:
        scanner = BleakScanner(detection_callback)
        await scanner.start()
        logger.info("Bluetooth scanner started successfully.")

        while True:
            await asyncio.sleep(5.0)

            # Prune old devices (not seen in 60 seconds)
            now = time.time()
            stale_macs = [
                mac
                for mac, data in discovered_devices.items()
                if now - data["last_seen"] > 60
            ]
            for mac in stale_macs:
                del discovered_devices[mac]
                try:
                    bluetooth_queue.put_nowait({"type": "device_removed", "mac": mac})
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Bluetooth scanner encountered an error: {e}")


async def aoa_serial_loop():
    """
    Listens for Bluetooth 5.1 Direction Finding (AoA) hardware on a serial port (e.g., /dev/ttyUSB0).
    Expects JSON lines like: {"mac": "AA:BB:CC:DD:EE:FF", "azimuth": 45, "elevation": 10}
    """
    try:
        import serial_asyncio
    except ImportError:
        logger.warning(
            "pyserial-asyncio not installed. AoA Direction Finding hardware support disabled."
        )
        return

    import json
    import os

    port = "/dev/ttyUSB99"
    baudrate = 115200

    while True:
        if not os.path.exists(port):
            await asyncio.sleep(5)
            continue

        try:
            reader, writer = await serial_asyncio.open_serial_connection(
                url=port, baudrate=baudrate
            )
            logger.info(f"Connected to AoA locator hardware on {port}")

            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    data = json.loads(line.decode("utf-8").strip())
                    mac = data.get("mac")
                    azimuth = data.get("azimuth")

                    if mac and azimuth is not None:
                        mac = str(mac).upper()
                        # If device already exists from BLE scanner, update it.
                        # Otherwise create a partial entry.
                        now = time.time()
                        if mac in discovered_devices:
                            discovered_devices[mac]["azimuth"] = azimuth
                            discovered_devices[mac]["last_seen"] = now
                        else:
                            discovered_devices[mac] = {
                                "mac": mac,
                                "name": "Unknown (AoA only)",
                                "rssi": data.get("rssi", -90),
                                "last_seen": now,
                                "azimuth": azimuth,
                            }

                        bluetooth_queue.put_nowait(
                            {"type": "device_update", "device": discovered_devices[mac]}
                        )
                except json.JSONDecodeError:
                    pass  # Ignore malformed serial lines
                except asyncio.CancelledError:
                    logger.info("Bluetooth AoA loop cancelled.")
                    break
        except Exception as e:
            logger.error(f"Bluetooth AoA Serial Error: {e}")
            await asyncio.sleep(5)


async def receive_agent_bluetooth_data(node_id: str, devices: list):
    """Processes Bluetooth devices scanned by remote Go agents."""
    now = time.time()

    for dev in devices:
        mac = dev.mac
        rssi = dev.rssi

        name = dev.name

        prev = discovered_devices.get(mac)
        should_emit = False

        if not prev:
            should_emit = True
            discovered_devices[mac] = {
                "mac": mac,
                "name": name,
                "rssi": rssi,
                "last_seen": now,
                "nodes": {node_id: {"rssi": rssi, "last_seen": now}},
            }
        else:
            # Update name if new
            if (
                prev.get("name", "Unknown Device") == "Unknown Device"
                and name != "Unknown Device"
            ):
                prev["name"] = name
                should_emit = True

            # Update node data
            if "nodes" not in prev:
                prev["nodes"] = {}
            prev["nodes"][node_id] = {"rssi": rssi, "last_seen": now}
            prev["last_seen"] = now

            # Recalculate top RSSI
            best_rssi = -1000
            for n_id, n_data in prev["nodes"].items():
                if n_data["rssi"] > best_rssi and now - n_data["last_seen"] < 60:
                    best_rssi = n_data["rssi"]

            old_rssi = prev.get("rssi", -1000)
            prev["rssi"] = best_rssi

            if abs(old_rssi - best_rssi) > 5:
                should_emit = True

        if should_emit:
            try:
                bluetooth_queue.put_nowait(
                    {"type": "device_update", "device": discovered_devices[mac]}
                )
            except Exception:
                pass


_aoa_task: Optional[asyncio.Task] = None


async def start_bluetooth_engine():
    global _scanner_task, _aoa_task
    if _scanner_task is None:
        _scanner_task = asyncio.create_task(bluetooth_scanner_loop())
    if _aoa_task is None:
        _aoa_task = asyncio.create_task(aoa_serial_loop())


async def stop_bluetooth_engine():
    global _scanner_task, _aoa_task
    if _scanner_task:
        _scanner_task.cancel()
        _scanner_task = None
    if _aoa_task:
        _aoa_task.cancel()
        _aoa_task = None
