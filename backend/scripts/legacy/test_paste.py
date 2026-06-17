import serial, time, sys

s = serial.Serial()
s.port = '/dev/ttyUSB0'
s.baudrate = 115200
s.dtr = False
s.rts = False
s.timeout = 0.5
s.open()

# Interrupt
s.write(b'\r\x03\x03\x03')
time.sleep(0.5)
s.read_all()

# Paste mode
s.write(b'\r\x05')
time.sleep(0.2)
s.write(b'import os, json\nprint("HELLO_PASTE")\n')
s.write(b'\x04')

out = b''
for _ in range(10):
    out += s.read(1024)
    if b'>>>' in out: break

s.close()
print("OUTPUT:")
print(out.decode('utf-8', errors='ignore'))
