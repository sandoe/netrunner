import serial, time, os

os.system("stty -F /dev/ttyUSB0 -hupcl")
s = serial.Serial()
s.port = "/dev/ttyUSB0"
s.baudrate = 115200
s._update_dtr_state = lambda: None
s._update_rts_state = lambda: None
s.open()
start = time.time()
out = b""
while time.time() - start < 2:
    if s.in_waiting:
        out += s.read(s.in_waiting)
s.close()
print("Output:", repr(out))
