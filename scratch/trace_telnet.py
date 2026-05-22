import socket
import time
import re

SHELL_PROMPTS = ["# ", "$ ", ":~# ", ":~$ ", "> "]
UNIQUE_PROMPT = "NR_PROMPT# "

class MockTelnetClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self._buf = b""

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.settimeout(0.3)

    def recv(self):
        try:
            return self.sock.recv(4096)
        except socket.timeout:
            return b""

    def read_until(self, patterns, timeout=10):
        bpats = [p.encode() for p in patterns]
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self.recv()
            if chunk:
                print("  [RECV CHUNK]:", repr(chunk))
                self._buf += chunk
            for p in bpats:
                idx = self._buf.find(p)
                if idx >= 0:
                    end = idx + len(p)
                    data, self._buf = self._buf[:end], self._buf[end:]
                    print("  [MATCHED PATTERN]:", repr(p))
                    print("  [REMAINING BUF]:", repr(self._buf))
                    return data.decode("utf-8", errors="replace")
            time.sleep(0.05)
        data, self._buf = self._buf, b""
        return data.decode("utf-8", errors="replace")

    def write(self, data):
        print("  [WRITE]:", repr(data))
        self.sock.sendall(data.encode() + b"\r\n")

    def _drain(self):
        print("  [DRAIN START]")
        prev = self.sock.gettimeout()
        self.sock.settimeout(0.01)
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                print("    [DRAINED CHUNK]:", repr(chunk))
            except socket.timeout:
                break
        self.sock.settimeout(prev)
        self._buf = b""
        print("  [DRAIN END]")

    def run_command(self, cmd):
        print(f"\n--- RUNNING COMMAND: {cmd} ---")
        self._drain()
        self.write(cmd)
        raw = self.read_until([UNIQUE_PROMPT])
        print("  [RAW OUTPUT]:", repr(raw))
        
        # Split lines
        lines = raw.split("\n")
        # Remove echo if present
        if lines and cmd.strip() in lines[0]:
            lines = lines[1:]
        
        # Strip prompt robustly
        if lines:
            if lines[-1].endswith(UNIQUE_PROMPT):
                lines[-1] = lines[-1][:-len(UNIQUE_PROMPT)]
            elif lines[-1].strip() == UNIQUE_PROMPT.strip():
                lines.pop()
        
        result = "\n".join(lines).strip()
        print("  [FINAL RESULT]:", repr(result))
        return result

def main():
    cl = MockTelnetClient("192.168.65.132", 5000)
    cl.connect()
    
    # Initialize
    cl.write("")
    cl.read_until(SHELL_PROMPTS + ["login:", "Login:", "Password:", "password:"], timeout=5)
    cl.write('export TERM=dumb; PS1="NR_PROMPT# "; stty -echo 2>/dev/null')
    cl.read_until([UNIQUE_PROMPT], timeout=5)
    
    # Run test commands
    cl.run_command("echo 'hello # world'")
    cl.run_command("echo 'hello > world'")
    cl.run_command("echo 'hello $ world'")
    cl.run_command("ip addr show")

if __name__ == "__main__":
    main()
