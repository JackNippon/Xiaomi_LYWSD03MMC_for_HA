import os
import utime as time
import machine

try:
    filename = 'main.py.bkp'
    f = open(filename, "r")
    f.close()
    # File exists
    os.rename('main.py.bkp', 'main.py')
    print('main.py restored. Restarting...')
    time.sleep(3)
    machine.reset()
except OSError:
    # File not found
    print('main.py.bkp not found.')