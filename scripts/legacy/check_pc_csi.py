import os
import subprocess
import glob

def check_wifi_hardware():
    print("--- 1. Checking WiFi Hardware ---")
    try:
        lspci_out = subprocess.check_output(["lspci"]).decode()
        network_devices = [line for line in lspci_out.split('\n') if 'Network' in line or 'Wireless' in line]
        if not network_devices:
            print("No wireless network controllers found via lspci.")
        for dev in network_devices:
            print(f"Found: {dev}")
    except FileNotFoundError:
        print("lspci command not found.")
    print("\n")

def check_csi_debugfs():
    print("--- 2. Checking for CSI DebugFS Interfaces ---")
    
    # Intel CSI Tool paths
    intel_paths = glob.glob('/sys/kernel/debug/iwlwifi/*/iwlmvm/csi')
    if intel_paths:
        print("✅ Intel CSI DebugFS interface found at:")
        for p in intel_paths:
            print(f"  - {p}")
    else:
        print("❌ Intel CSI DebugFS interface NOT found.")

    # Nexmon CSI paths (usually just a UDP stream or specific netlink, but checking for nexmon in dmesg)
    try:
        nexmon_check = subprocess.check_output(["dmesg"]).decode()
        if 'nexmon' in nexmon_check.lower():
            print("✅ Nexmon firmware traces found in dmesg.")
        else:
            print("❌ Nexmon firmware NOT detected in dmesg.")
    except Exception:
        print("Could not read dmesg to check for Nexmon.")

    # Atheros CSI Tool (requires custom kernel)
    ath_path = '/sys/kernel/debug/ath9k/'
    if os.path.exists(ath_path):
        print("✅ Atheros ath9k debugfs found (may support CSI with custom kernel).")
    else:
        print("❌ Atheros ath9k debugfs NOT found.")
    print("\n")

def try_read_csi():
    print("--- 3. Attempting to read CSI data ---")
    intel_paths = glob.glob('/sys/kernel/debug/iwlwifi/*/iwlmvm/csi')
    if intel_paths:
        try:
            print(f"Attempting to read from {intel_paths[0]}...")
            with open(intel_paths[0], 'rb') as f:
                data = f.read(1024)
                if data:
                    print(f"SUCCESS: Read {len(data)} bytes of raw CSI data.")
                else:
                    print("File opened, but no data available. You might need to send ping packets.")
        except PermissionError:
            print("PERMISSION DENIED: You need root (sudo) privileges to read CSI data.")
        except Exception as e:
            print(f"Error reading CSI data: {e}")
    else:
        print("No supported hardware interface found to extract real CSI data.")
        print("Standard PC WiFi cards require modified firmware (like Linux 802.11n CSI Tool for Intel 5300, or Nexmon for Broadcom) to extract CSI.")

if __name__ == "__main__":
    check_wifi_hardware()
    check_csi_debugfs()
    try_read_csi()
