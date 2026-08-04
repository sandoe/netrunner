import serial, time

serial.Serial._update_dtr_state = lambda self: None
serial.Serial._update_rts_state = lambda self: None
s = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
s.write(b"\r\x03\x03")
time.sleep(0.5)
out = s.read_all()
s.close()
print("Interrupt Output:", repr(out))
