import subprocess
print("Running interrupt...")
subprocess.run(["python3", "-c", "import serial, time; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; s=serial.Serial('/dev/ttyUSB0', 115200, timeout=1); s.write(b'\\r\\x03\\x03'); time.sleep(0.5); s.read_all(); s.close()"])
print("Running mpremote ls...")
res = subprocess.run(["timeout", "15", "python3", "-c", "import sys, serial; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; from mpremote.main import main; sys.argv=['mpremote', 'connect', '/dev/ttyUSB0', 'ls']; sys.exit(main())"], capture_output=True, text=True)
print("Return code:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
