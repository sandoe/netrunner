import subprocess, time, serial

subprocess.run(
    "stty -F /dev/ttyUSB0 -hupcl; python3 -c \"import sys, serial; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; from mpremote.main import main; sys.argv=['mpremote', 'connect', '/dev/ttyUSB0', 'ls']; sys.exit(main())\"",
    shell=True,
)

# Now quickly open the port and see what it outputs!
s = serial.Serial("/dev/ttyUSB0", 115200, timeout=2)
s.dtr = False
s.rts = False
print("Output after mpremote ls:", repr(s.read_all()))
s.close()
