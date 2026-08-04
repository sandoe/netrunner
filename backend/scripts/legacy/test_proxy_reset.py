import subprocess, time

print("Interrupting...")
subprocess.run(
    [
        "python3",
        "-c",
        "import serial, time; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; s=serial.Serial('/dev/ttyUSB0', 115200, timeout=1); s.write(b'\\r\\x03\\x03'); time.sleep(0.5); s.read_all(); s.close()",
    ]
)

print("Running py_proxy...")
p = subprocess.Popen(
    [
        "python3",
        "-c",
        """
import sys, select, time
import serial
serial.Serial._update_dtr_state = lambda self: None
serial.Serial._update_rts_state = lambda self: None
s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)
start = time.time()
while time.time() - start < 2:
    if s.in_waiting:
        sys.stdout.buffer.write(s.read(s.in_waiting))
""",
    ],
    stdout=subprocess.PIPE,
)

out, _ = p.communicate()
print("Proxy output:", repr(out))
