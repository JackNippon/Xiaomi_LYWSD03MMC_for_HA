import utime as time
from umqtt.simple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
esp.osdebug(None)
import gc
gc.collect()
import ble, ntptime
import uos
import utils
import logging, logger
logger.initLogging()

# NOTE: configuration parameters are stored in "config.py" file.
# Rename "config_example.py" file to "config.py" and fill with your settings
from config import *
global wifi_ssid, wifi_password, client_id, mqtt_server, mqtt_port, mqtt_user, mqtt_password, topic_sub


client_id = ubinascii.hexlify(machine.unique_id())


def connect_wifi():
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(wifi_ssid, wifi_password)
    while not station.isconnected():
        pass
    logging.info('Connection successful {}', station.ifconfig())


def update_time():
    try:
        ntptime.settime()
        logging.info('Time updated: {}', utils.timestamp())
    except Exception as e:
        utils.log_error_to_file('ERROR: ntptime settime - ' + str(e))


def connect_mqtt():
    #client = MQTTClient(client_id, mqtt_server)
    client = MQTTClient(client_id, mqtt_server, mqtt_port, mqtt_user, mqtt_password)
    client.connect()
    logging.info('Connected to {} MQTT broker', mqtt_server)
    return client


def restart_and_reconnect():
    logging.error('Failed to connect to MQTT broker. Restarting in 10 seconds...')
    time.sleep(10)
    machine.reset()


def cleanup():
    logging.info('Starting cleanup...')
    dir = uos.listdir()
    for f in dir:
        logging.info('Found file: {}', f)
        try:
            year = int(f[:4])
            month = int(f[4:6])
            mday = int(f[6:8])
            # print(year, month, mday)
            filedate = time.mktime((year, month, mday, 0, 0, 0, 0, 0))
            year, month, mday, hour, minute, second, weekday, yearday = time.localtime()
            two_days_ago = time.mktime((year, month, mday-2, 0, 0, 0, 0, 0))
            # print(filedate, two_days_ago)
            if filedate < two_days_ago:
                logging.debug('Removing...')
                uos.remove(f)
            else:
                logging.debug('Keeping...')

        except Exception as e:
            # logging.error('ERROR: cleanup {}', str(e))
            logging.debug('Skipping...')
            pass
    logging.info('Cleanup ended')


# Start execution

connect_wifi()
update_time()

try:
    client = connect_mqtt()
except OSError as e:
    restart_and_reconnect()

myBLE = ble.ble()
myBLE.setup()

for a in myBLE.addresses:
    type, address, name = a
    logging.info('Device found - Address: {} - Name: {}', utils.prettify(address), name)

lastday = 0
while True:
    # update the RTC once a day
    today = utils.timestamp('day')
    if today != lastday:
        try:
            ntptime.settime()
            lastday = today
            logging.info('Time set from server: {}', utils.timestamp())
        except Exception as e:
            utils.log_error_to_file('ERROR: ntptime - ' + str(e))

    # cleanup filesystem
    cleanup()

    # cycle through the captured addresses
    for a in myBLE.addresses:
        type, myBLE.address, name = a
        # if this is a 'LYWSD03MMC'
        if name == 'LYWSD03MMC':
            print('\r\n----------------------------------------------------------')
            # if we are successful reading the values
            if (myBLE.get_reading()):
                message = '{"temperature": "' + str(myBLE.temperature) + '", '
                message = message + '"humidity": "' + str(myBLE.humidity) + '", '
                message = message + '"batteryLevel": "' + str(myBLE.battery_level) + '", '
                message = message + '"batteryVoltage": "' + str(myBLE.battery_voltage) + '"}'
                logging.debug('Message: {}', message)
                topic = topic_pub + '/' + ''.join('{:02x}'.format(b) for b in myBLE.address)
                logging.debug('Topic: {}', topic)
                try:
                    client.publish(topic, message)
                except Exception as e:
                    utils.log_error_to_file('ERROR: publish - ' + str(e))
                    try:
                        client.disconnect()
                        client = connect_mqtt()
                    except OSError as e:
                        restart_and_reconnect()

    # wait a minute for the next one
    time.sleep(60)

