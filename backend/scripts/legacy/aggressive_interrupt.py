import serial, time
s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)
s.dtr = False
s.rts = False
for _ in range(10):
    s.write(b'\r\x03\x03')
    time.sleep(0.1)
    s.read_all()
s.close()
