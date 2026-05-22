import socket
import sys
import time

class TelnetHandler:
    def __init__(self, cols: int = 220, rows: int = 50):
        self.state = "data"
        self.sb_buf = bytearray()
        self.option = None
        self.cmd = None
        self.cols = cols
        self.rows = rows

    def feed(self, data: bytes) -> tuple[bytes, bytes]:
        clean_data = bytearray()
        response = bytearray()
        
        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            if self.state == "data":
                if b == 255: # IAC
                    self.state = "iac"
                else:
                    clean_data.append(b)
            elif self.state == "iac":
                if b in (251, 252, 253, 254): # WILL, WONT, DO, DONT
                    self.cmd = b
                    self.state = "opt"
                elif b == 250: # SB
                    self.state = "sb"
                    self.sb_buf.clear()
                elif b == 255: # Escaped IAC
                    clean_data.append(255)
                    self.state = "data"
                else:
                    self.state = "data"
            elif self.state == "opt":
                opt = b
                if self.cmd == 253: # DO
                    if opt == 1: # ECHO
                        response.extend(b"\xff\xfc\x01")
                    elif opt == 3: # SUPPRESS GO AHEAD
                        response.extend(b"\xff\xfb\x03")
                    elif opt == 24: # TERMINAL TYPE
                        response.extend(b"\xff\xfb\x18")
                    elif opt == 31: # NAWS (Window size)
                        response.extend(b"\xff\xfb\x1f")
                        response.extend(self.resize(self.cols, self.rows))
                    else:
                        response.extend(bytes([255, 252, opt]))
                elif self.cmd == 254: # DONT
                    response.extend(bytes([255, 252, opt]))
                elif self.cmd == 251: # WILL
                    if opt == 1: # ECHO
                        response.extend(b"\xff\xfd\x01")
                    elif opt == 3: # SUPPRESS GO AHEAD
                        response.extend(b"\xff\xfd\x03")
                    else:
                        response.extend(bytes([255, 253, opt]))
                elif self.cmd == 252: # WONT
                    response.extend(bytes([255, 254, opt]))
                self.state = "data"
            elif self.state == "sb":
                if b == 255: # IAC
                    self.state = "sb_iac"
                else:
                    self.sb_buf.append(b)
            elif self.state == "sb_iac":
                if b == 240: # SE
                    if len(self.sb_buf) > 1 and self.sb_buf[0] == 24: # TERMINAL TYPE
                        if self.sb_buf[1] == 1: # SEND
                            response.extend(b"\xff\xfa\x18\x00xterm-256color\xff\xf0")
                    self.state = "data"
                else:
                    self.sb_buf.append(255)
                    self.sb_buf.append(b)
                    self.state = "sb"
            i += 1
            
        return bytes(clean_data), bytes(response)

    def resize(self, cols: int, rows: int) -> bytes:
        self.cols = cols
        self.rows = rows
        w_h = (cols >> 8) & 0xff
        w_l = cols & 0xff
        h_h = (rows >> 8) & 0xff
        h_l = rows & 0xff
        return bytes([255, 250, 31, w_h, w_l, h_h, h_l, 255, 240])

def main():
    host = "192.168.65.132"
    port = 5000
    s = socket.create_connection((host, port), timeout=5)
    s.settimeout(0.1)
    
    handler = TelnetHandler()
    
    # 1. Connect and read
    print("[CONN]")
    for _ in range(5):
        try:
            data = s.recv(4096)
            if not data:
                break
            print("  <- RAW:", repr(data))
            clean, resp = handler.feed(data)
            if clean:
                print("  <- CLEAN:", repr(clean))
            if resp:
                print("  -> SEND RESP:", repr(resp))
                s.sendall(resp)
        except socket.timeout:
            break
            
    # Send newline
    print("[SEND NEWLINE]")
    s.sendall(b"\r\n")
    
    # Read response
    for _ in range(10):
        try:
            data = s.recv(4096)
            if not data:
                break
            print("  <- RAW:", repr(data))
            clean, resp = handler.feed(data)
            if clean:
                print("  <- CLEAN:", repr(clean))
            if resp:
                print("  -> SEND RESP:", repr(resp))
                s.sendall(resp)
        except socket.timeout:
            time.sleep(0.1)
            
    # Try typing something and see if it echoes back
    print("[TYPE 'help']")
    s.sendall(b"h")
    time.sleep(0.05)
    try:
        data = s.recv(4096)
        print("  Typed 'h', <- RAW:", repr(data))
    except socket.timeout:
        print("  Typed 'h', <- TIMEOUT (No echo!)")

    s.close()

if __name__ == "__main__":
    main()
