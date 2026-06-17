import sys
import json
import time
import serial
from mpremote.transport_serial import SerialTransport
from mpremote_api import MPRemote

def open_serial(port: str, timeout: float = 0.05, retries: int = 3) -> serial.Serial:
    """Åbn porten UDEN at toggle DTR/RTS.

    pyserial asserter DTR/RTS ved open() som standard - på ESP32 dev-boards
    trigger det auto-reset kredsløbet (EN/IO0) og hard-resetter chippen.
    """
    last_err = None
    for attempt in range(retries):
        try:
            s = serial.Serial()
            s.port = port
            s.baudrate = 115200
            s.timeout = timeout
            # SKAL sættes før open() for at undgå DTR/RTS-puls
            s.dtr = False
            s.rts = False
            s.open()
            _disable_hupcl(s)
            return s
        except Exception as e:
            last_err = e
            if "readiness to read" in str(e) or "EAGAIN" in str(e):
                time.sleep(1.0)
                continue
            raise
    raise Exception(f"Failed to open port after {retries} attempts: {last_err}")

def _disable_hupcl(s: serial.Serial) -> None:
    """Slå HUPCL fra, så DTR ikke droppes når porten lukkes.

    Ellers hard-resetter ESP32'en hver gang processen afslutter.
    """
    try:
        import termios
        attrs = termios.tcgetattr(s.fd)
        attrs[2] &= ~termios.HUPCL
        termios.tcsetattr(s.fd, termios.TCSANOW, attrs)
    except Exception:
        pass

def send_ctrl(port: str, seq) -> None:
    """Send control-bytes uden eksklusiv åbning og uden REPL-handshake.

    Kan bruges mens en mpremote REPL-session holder porten åben.
    """
    s = open_serial(port, timeout=0.5)
    try:
        for b in seq:
            s.write(b)
            s.flush()
            time.sleep(0.1)
    finally:
        s.close()

def fix_serial_port(port: str) -> serial.Serial:
    s = open_serial(port)

    start = time.monotonic()
    quiet_since = None
    while time.monotonic() - start < 3.0:
        try:
            s.write(b'\r\x02\x03')
            chunk = s.read(s.in_waiting or 1)
            if chunk:
                quiet_since = None
            else:
                if quiet_since is None: quiet_since = time.monotonic()
                elif time.monotonic() - quiet_since >= 0.5: break
        except Exception as e:
            if "readiness to read" in str(e):
                s.close()
                time.sleep(0.5)
                s = open_serial(port)
            else:
                raise e
            
    s.reset_input_buffer()
    s.write(b'\r\x03')
    s.flush()
    time.sleep(0.2)
    s.read(s.in_waiting or 1)
    
    s.timeout = 5.0
    return s

def run_command(port, cmd, args):
    # stop/reset/fix håndteres uden MPRemote og uden REPL-handshake,
    # så en åben REPL-session overlever og ESP'en ikke forstyrres unødigt.
    if cmd == "stop":
        # Ctrl-C x2: afbryd kørende program (soft, ingen reset)
        send_ctrl(port, [b'\x03', b'\x03'])
        return json.dumps({"status": "ok"})

    if cmd == "reset":
        # Ctrl-C x2 + Ctrl-D: soft reset (genstarter MicroPython VM, ikke chippen)
        send_ctrl(port, [b'\x03', b'\x03', b'\x04'])
        return json.dumps({"status": "ok"})

    if cmd == "fix":
        # Bare verificér at porten kan åbnes - send IKKE Ctrl-C,
        # ellers stopper "connect" det kørende program på ESP'en.
        s = open_serial(port)
        s.close()
        return json.dumps({"status": "ok"})

    s = fix_serial_port(port)
    
    old_init = SerialTransport.__init__
    def patched_init(self, device, baudrate=115200, wait=0, exclusive=True, timeout=None):
        self.in_raw_repl = False
        self.use_raw_paste = True
        self.device_name = device
        self.mounted = False
        self.serial = s 
        
    SerialTransport.__init__ = patched_init
    
    dev = MPRemote(port)
    dev._connect_timeout = 2.0
    dev.connect()

    try:
        if cmd == "ls":
            path = args[0] if len(args) > 0 else "/"
            entries = dev.ls(path)
            return json.dumps([{"name": e.name, "is_dir": e.is_dir, "size": e.size} for e in entries])
            
        elif cmd == "read":
            path = args[0]
            return dev.read_text(path)
            
        elif cmd == "write":
            path = args[0]
            local_tmp = args[1]
            with open(local_tmp, "r") as f:
                dev.write_text(path, f.read())
            return json.dumps({"status": "ok"})
            
        elif cmd == "put":
            import os
            local_path = args[0]
            remote_path = args[1]
            if os.path.isdir(local_path):
                for item in os.listdir(local_path):
                    lp = os.path.join(local_path, item)
                    rp = dev._join(remote_path, item) if hasattr(dev, '_join') else remote_path.rstrip('/') + '/' + item
                    if remote_path == "/": rp = "/" + item
                    dev.put(lp, rp, recursive=True)
            else:
                dev.put(local_path, remote_path, recursive=True)
            return json.dumps({"status": "ok"})
        elif cmd == "rm":
            path = args[0]
            dev.rm(path)
            return json.dumps({"status": "ok"})
            
        elif cmd == "mkdir":
            path = args[0]
            dev.mkdir(path)
            return json.dumps({"status": "ok"})
            
        elif cmd == "run":
            path = args[0]
            with open(path, 'r') as f:
                content = f.read()
            out = dev.exec(content)
            return json.dumps({"status": "ok", "output": out})
            
        else:
            return json.dumps({"error": "Unknown command"})
            
    finally:
        try: dev.disconnect()
        except: pass
        try: s.close()
        except: pass
        SerialTransport.__init__ = old_init

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    port = sys.argv[1]
    cmd = sys.argv[2]
    args = sys.argv[3:]
    
    # Retry the entire operation up to 3 times for flaky hardware
    last_err = None
    for attempt in range(3):
        try:
            result = run_command(port, cmd, args)
            print(result)
            return
        except Exception as e:
            last_err = str(e)
            if "readiness to read" in last_err or "could not enter raw repl" in last_err:
                time.sleep(1.0)
                continue
            break
            
    print(json.dumps({"error": last_err}))

if __name__ == "__main__":
    main()
