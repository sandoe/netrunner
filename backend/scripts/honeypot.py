import socket
import threading
import time
import json
import sys

LOG_FILE = "/tmp/netrunner-honeypot.log"
PORT = 2121  # Fake FTP port

def handle_client(client_socket, address):
    ip, port = address
    try:
        client_socket.send(b"220 (vsFTPd 3.0.3)\r\n")
        data = client_socket.recv(1024).decode(errors='ignore').strip()
        
        if data.startswith("USER"):
            client_socket.send(b"331 Please specify the password.\r\n")
            pass_data = client_socket.recv(1024).decode(errors='ignore').strip()
            
            entry = {
                "timestamp": time.time(),
                "event": "honeypot_login",
                "attacker_ip": ip,
                "port": PORT,
                "payload": f"{data} | {pass_data}"
            }
            
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
                
            client_socket.send(b"530 Login incorrect.\r\n")
    except Exception:
        pass
    finally:
        client_socket.close()

def main():
    print(f"Starting Netrunner Honeypot on port {PORT}... Logging to {LOG_FILE}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(("0.0.0.0", PORT))
        server.listen(5)
        while True:
            client, addr = server.accept()
            # Log connection attempt immediately
            entry = {
                "timestamp": time.time(),
                "event": "honeypot_connect",
                "attacker_ip": addr[0],
                "port": PORT,
                "payload": "CONNECTION_ESTABLISHED"
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
                
            client_handler = threading.Thread(target=handle_client, args=(client, addr))
            client_handler.start()
    except Exception as e:
        print(f"Honeypot failed: {e}")

if __name__ == "__main__":
    main()
