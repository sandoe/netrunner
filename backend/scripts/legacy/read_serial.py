import serial, time

s = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
s.dtr = False
s.rts = False
s.write(b"\r")
time.sleep(1)
print("Output:", s.read_all())
