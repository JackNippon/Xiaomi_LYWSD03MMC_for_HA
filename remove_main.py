import os
import utime as time
import machine

try:
    filename = 'main.py'
    f = open(filename, "r")
    f.close()
    # File exists
    os.rename('main.py', 'main.py.bkp')
    print('main.py removed. Restarting...')
    time.sleep(3)
    machine.reset()
except OSError:
    # File not found
    print('main.py not found.')