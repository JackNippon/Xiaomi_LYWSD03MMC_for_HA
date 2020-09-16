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
        if f.endswith('.log'):
            logging.info('Found file: {}', f)
            try:
                year = int(f[:4])
                month = int(f[4:6])
                mday = int(f[6:8])
                filedate = time.mktime((year, month, mday, 0, 0, 0, 0, 0))
                year, month, mday, hour, minute, second, weekday, yearday = time.localtime()
                two_days_ago = time.mktime((year, month, mday-2, 0, 0, 0, 0, 0))
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
cleanup()

try:
    mqtt_client = connect_mqtt()
except OSError as e:
    restart_and_reconnect()

myBLE = ble.Ble()
myBLE.setup(scan_for_devices, devices_list)

for a in myBLE.addresses:
    device_index, type, address, name, last_read = a
    logging.info('Device found - Type: {} - Address: {} - Name: {}', type, utils.decode_mac(address), name)

last_time_update = utils.timestamp('day')
last_cleanup = utils.timestamp('day')
last_scan = time.time()
while True:
    today = utils.timestamp('day')
    current_time = time.time()

    # Update the RTC once a day
    if today != last_time_update:
        update_time()
        last_time_update = today

    # Cleanup filesystem once a day
    if today != last_cleanup:
        cleanup()
        last_cleanup = today

    # Re-scan for devices every <scan_interval> seconds
    if current_time > last_scan + scan_interval:
        myBLE.setup(scan_for_devices, devices_list)
        last_scan = current_time

    # Cycle through the captured addresses
    oldest_read = current_time + read_interval
    for a in myBLE.addresses:
        myBLE.device_index, myBLE.type, myBLE.address, myBLE.name, myBLE.last_read = a
        # if this is a 'LYWSD03MMC'
        if myBLE.name == 'LYWSD03MMC' and (time.time() - myBLE.last_read >= read_interval):
            print('--------------------------------------------------')
            # if we are successful reading the values
            if myBLE.get_reading():
                message = '{"temperature": "' + str(myBLE.temperature) + '", '
                message = message + '"humidity": "' + str(myBLE.humidity) + '", '
                message = message + '"batteryLevel": "' + str(myBLE.battery_level) + '", '
                message = message + '"batteryVoltage": "' + str(myBLE.battery_voltage) + '"}'
                logging.debug('Message: {}', message)
                topic = topic_pub + '/' + ''.join('{:02x}'.format(b) for b in myBLE.address)
                logging.debug('Topic: {}', topic)
                try:
                    mqtt_client.publish(topic, message)
                except Exception as e:
                    utils.log_error_to_file('ERROR: publish to MQTT - ' + str(e))
                    try:
                        mqtt_client.disconnect()
                        mqtt_client = connect_mqtt()
                    except OSError as e:
                        restart_and_reconnect()

        if oldest_read > myBLE.last_read:
            oldest_read = myBLE.last_read

    # Wait for the next cycle
    now = time.time()
    if oldest_read < now:
        delay = read_interval - now + oldest_read
        if delay > 0:
            print('--------------------------------------------------')
            logging.debug('Waiting for {} seconds...', delay)
            time.sleep(delay)

