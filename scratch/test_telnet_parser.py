# Test TelnetHandler parsing and option negotiation

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
                        # Send our current window size as a subnegotiation
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


# Run tests
handler = TelnetHandler()

# 1. Test clean data parsing
clean, resp = handler.feed(b"Hello World")
assert clean == b"Hello World"
assert resp == b""

# 2. Test IAC stripping
clean, resp = handler.feed(b"\xff\xfb\x01Hello")
assert clean == b"Hello"
assert resp == b"\xff\xfd\x01" # Should answer DO ECHO to WILL ECHO

# 3. Test subnegotiation of Terminal Type
clean, resp = handler.feed(b"\xff\xfd\x18") # DO TERMINAL TYPE
assert clean == b""
assert resp == b"\xff\xfb\x18" # Reply WILL TERMINAL TYPE

clean, resp = handler.feed(b"\xff\xfa\x18\x01\xff\xf0") # SB TERMINAL TYPE SEND SE
assert clean == b""
assert resp == b"\xff\xfa\x18\x00xterm-256color\xff\xf0" # Reply IS xterm-256color

# 4. Test resize NAWS
resize_bytes = handler.resize(100, 40)
assert resize_bytes == b"\xff\xfa\x1f\x00\x64\x00\x28\xff\xf0"

print("All tests passed successfully!")
