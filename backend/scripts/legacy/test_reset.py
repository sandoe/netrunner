import serial, time

print("Opening port...")
s = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
s.dtr = False
s.rts = False
print("Port opened. Reading 2 seconds of output...")
start = time.time()
out = b""
while time.time() - start < 2:
    out += s.read_all()
s.close()
print("Output:", repr(out))
