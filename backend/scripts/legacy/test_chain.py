import subprocess
print("Interrupting...")
subprocess.run(["python3", "-c", "import serial, time; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; s=serial.Serial('/dev/ttyUSB0', 115200, timeout=1); s.write(b'\\r\\x03\\x03'); time.sleep(0.5); print('Out:', s.read_all()); s.close()"])
print("Listing...")
subprocess.run(["python3", "-c", "import sys, serial; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; from mpremote.main import main; sys.argv=['mpremote', 'connect', '/dev/ttyUSB0', 'ls']; sys.exit(main())"])
