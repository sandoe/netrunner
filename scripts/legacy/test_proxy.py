import sys, select, time
try:
    import serial
    serial.Serial._update_dtr_state = lambda self: None
    serial.Serial._update_rts_state = lambda self: None
    s = serial.Serial('ttyUSB0', 115200, timeout=0)
    s.dtr = False
    s.rts = False
    time.sleep(0.1)
    s.dtr = True
    time.sleep(0.1)
    s.dtr = False
    time.sleep(0.2)
    
    while True:
        try:
            s.open()
            try:
                while True:
                    r, _, _ = select.select([sys.stdin, s], [], [])
                    if sys.stdin in r:
                        d = sys.stdin.buffer.read1(1024)
                        if not d: sys.exit(0) # EOF from SSH
                        s.write(d)
                    if s in r:
                        d = s.read(1024)
                        if d: sys.stdout.buffer.write(d); sys.stdout.buffer.flush()
            finally:
                s.close()
        except Exception as e:
            msg = str(e)
            if 'device reports readiness' in msg or 'I/O error' in msg or 'Permission denied' in msg:
                sys.stdout.write(f'\r\n\x1b[33m[SYSTEM] Port busy or error: {msg}. Retrying in 1.5s...\x1b[0m\r\n')
                sys.stdout.flush()
                time.sleep(1.5)
            else:
                sys.stdout.write(msg + '\n')
                break
except Exception as e:
    sys.stdout.write(f'\r\n\x1b[31m[PROXY ERROR] {str(e)}\x1b[0m\r\n')
    sys.exit(1)
