import serial, time

s = serial.Serial("/dev/ttyUSB0", 115200)
s.dtr = True
s.rts = True
time.sleep(0.1)
s.dtr = False
s.rts = False
time.sleep(1)
print("Output:", s.read_all())
