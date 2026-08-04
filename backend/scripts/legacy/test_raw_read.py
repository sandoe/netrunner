import os

try:
    fd = os.open("/dev/ttyUSB0", os.O_RDWR | os.O_NONBLOCK)
    print("FD:", fd)
    os.set_blocking(fd, False)
    try:
        print("READ:", os.read(fd, 10))
    except BlockingIOError:
        print("READ: BlockingIOError (no data yet)")
except Exception as e:
    print("ERROR:", e)
