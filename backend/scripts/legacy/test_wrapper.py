import sys
import serial
serial.Serial._update_dtr_state = lambda self: None
serial.Serial._update_rts_state = lambda self: None
from mpremote.main import main
sys.argv = ['mpremote', 'connect', '/dev/ttyUSB0', 'ls']
sys.exit(main())
