import serial
serial.Serial._update_dtr_state = lambda self: None
serial.Serial._update_rts_state = lambda self: None
s = serial.Serial('/dev/ttyUSB0', 115200)
s.close()
