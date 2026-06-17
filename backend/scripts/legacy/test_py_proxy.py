import sys, select, time
try:
    import serial
    serial.Serial._update_dtr_state = lambda self: None
    serial.Serial._update_rts_state = lambda self: None
    s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)

    start = time.time()
    out = b''
    while time.time() - start < 3:
        if s.in_waiting:
            out += s.read(s.in_waiting)
        time.sleep(0.01)
    print("Proxy Output:", repr(out))
    s.close()
except Exception as e:
    print("Error:", e)
