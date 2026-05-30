# boot.py
import network
import time
import machine

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print('.', end='')
            
    if wlan.isconnected():
        print('\nNetwork connected!')
        print('IP address:', wlan.ifconfig()[0])
    else:
        print('\nFailed to connect to WiFi!')
        machine.reset() # Reboot and try again

connect_wifi()
