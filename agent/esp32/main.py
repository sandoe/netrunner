import time
import ota_updater

# Always check for updates at boot
try:
    ota_updater.check_for_updates()
except Exception as e:
    print("Failed to check for OTA updates:", e)

print("\n--- Netrunner ESP32 Node Started ---")
print("Running version: v1.0.0")

# Your custom sensor/wifi logic goes here
while True:
    print("ESP32 is active and waiting for instructions...")
    time.sleep(5)
