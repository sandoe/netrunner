import serial, time

s = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.1)
s.dtr = False
s.rts = False
for _ in range(10):
    s.write(b"\r\x03\x03")
    time.sleep(0.1)
    s.read_all()

# Now try to enter raw repl manually
s.write(b"\r\x01")
time.sleep(0.1)
s.read_all()

# Send python code to rename main.py
code = b'import os; os.rename("main.py", "main_bak.py")\r\x04'
s.write(code)
time.sleep(0.5)
print("Out:", s.read_all())
s.write(b"\r\x02")  # Exit raw repl
s.close()
