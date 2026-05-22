import socket
import sys

def main():
    host = "192.168.65.132"
    port = 5000
    print(f"Connecting to {host}:{port}...")
    s = socket.create_connection((host, port), timeout=5)
    s.settimeout(1)
    
    # Read anything immediately
    try:
        data = s.recv(4096)
        print("Received immediately:", repr(data))
        print("Received hex:", data.hex())
    except Exception as ex:
        print("No immediate data:", ex)

    # Send a newline to trigger prompt
    s.sendall(b"\r\n")
    try:
        data = s.recv(4096)
        print("Received after newline:", repr(data))
        print("Received hex:", data.hex())
    except Exception as ex:
        print("No data after newline:", ex)

    s.close()

if __name__ == "__main__":
    main()
