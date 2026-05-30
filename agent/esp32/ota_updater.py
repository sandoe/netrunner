import urequests
import os
import machine
import time

# IP of the machine running Netrunner (e.g. your PC)
SERVER_IP = "192.168.1.100" 
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

VERSION_FILE = "version.txt"

def get_current_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"

def save_new_version(version):
    with open(VERSION_FILE, "w") as f:
        f.write(version)

def check_for_updates():
    print(f"Checking for updates at {SERVER_URL}...")
    try:
        current_version = get_current_version()
        print(f"Current version: {current_version}")
        
        response = urequests.get(f"{SERVER_URL}/api/esp32/version")
        if response.status_code == 200:
            latest_version = response.json().get("version")
            print(f"Latest version available: {latest_version}")
            
            if latest_version != current_version:
                print("New version found! Downloading...")
                download_and_install(latest_version)
            else:
                print("System is up to date.")
        else:
            print(f"Server returned status {response.status_code}")
        response.close()
    except Exception as e:
        print(f"Error checking for updates: {e}")

def download_and_install(new_version):
    try:
        response = urequests.get(f"{SERVER_URL}/api/esp32/download")
        if response.status_code == 200:
            print("Download successful. Saving to main.py...")
            with open("main.py", "w") as f:
                f.write(response.text)
            
            save_new_version(new_version)
            print("Update installed successfully. Rebooting...")
            time.sleep(1)
            machine.reset()
        else:
            print(f"Failed to download update. Status: {response.status_code}")
        response.close()
    except Exception as e:
        print(f"Error downloading update: {e}")

if __name__ == "__main__":
    check_for_updates()
