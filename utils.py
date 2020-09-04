import machine, ntptime
import binascii
import logging, logger
logger.initLogging()


def decode_mac(mac_bytes):
    return ':'.join('{:02x}'.format(b) for b in mac_bytes)


def encode_mac(mac_string):
    # return mac_string.replace(':', '').decode('hex')
    return binascii.unhexlify(mac_string.replace(b':', b''))


def timestamp(type='timestamp'):
    yy,mm,dd,dy,hh,MM,ss,ms = machine.RTC().datetime()
    if type == 'day':
        return dd
    elif type == 'hour':
        return hh
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