import subprocess

print("Testing mpremote ls with advanced patch...")
p = subprocess.run(
    "stty -F /dev/ttyUSB0 -hupcl; python3 -c \"import sys, serial; serial.Serial._update_dtr_state = lambda self: None; serial.Serial._update_rts_state = lambda self: None; orig=serial.Serial.open; serial.Serial.open = lambda self: (orig(self), self.reset_input_buffer(), self.reset_output_buffer()); from mpremote.main import main; sys.argv=['mpremote', 'connect', '/dev/ttyUSB0', 'ls']; sys.exit(main())\"",
    shell=True,
    capture_output=True,
    text=True,
)
print("Return code:", p.returncode)
print("Stdout:", p.stdout)
print("Stderr:", p.stderr)
