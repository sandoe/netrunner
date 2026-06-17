import os, termios, time

# Clear HUPCL before doing anything
os.system("stty -F /dev/ttyUSB0 -hupcl")

# Open port with O_NONBLOCK so it doesn't wait for carrier
fd = os.open('/dev/ttyUSB0', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

# We can read output for 2 seconds to see if it reset
print("Reading output...")
start = time.time()
out = b''
while time.time() - start < 2:
    try:
        data = os.read(fd, 1024)
        out += data
    except BlockingIOError:
        time.sleep(0.1)

os.close(fd)
print("Output:", repr(out))
