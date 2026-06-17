import subprocess, time
subprocess.run(["fuser", "-k", "-9", "/dev/ttyUSB0"], stderr=subprocess.DEVNULL)
time.sleep(1)
subprocess.run("stty -F /dev/ttyUSB0 -hupcl; python3 -c \"import serial, time; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; s=serial.Serial('/dev/ttyUSB0', 115200, timeout=1); s.write(b'\\r\\x03\\x03'); time.sleep(0.5); s.read_all(); s.close()\"", shell=True)
p = subprocess.Popen(["python3", "-c", "import sys, select, time, serial; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0); start = time.time(); out=b'';\nwhile time.time() - start < 2:\n if s.in_waiting: out+=s.read(s.in_waiting)\nprint('Proxy Out:', repr(out))"], stdout=subprocess.PIPE)
out, _ = p.communicate()
print(out.decode())
