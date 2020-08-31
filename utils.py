import machine, ntptime
import logging, logger
logger.initLogging()

def prettify(mac_string):
    return ':'.join('{:02x}'.format(b) for b in mac_string)

def timestamp(type='timestamp'):
    yy,mm,dd,dy,hh,MM,ss,ms = machine.RTC().datetime()
    if type == 'day':
        return dd
    elif type == 'date':
        return '{:04d}{:02d}{:02d}'.format(yy,mm,dd)

    else:
        return '{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(yy,mm,dd,hh,MM,ss)

def log_error_to_file(message, fname ='ble.log'):
    try:
        f = open(timestamp(type='date') + fname, 'a')
        f.write(timestamp() + ' ' + message + '\n')
        f.close()
    except Exception as e:
        logging.error('ERROR: log_error_to_file - {}', str(e))

    logging.error(message)