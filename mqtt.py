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

# NOTE: configuration parameters are stored in "config.py" file.
# Rename "config_example.py" file to "config.py" and fill with your settings
from config import *
global wifi_ssid, wifi_password, client_id, mqtt_server, mqtt_port, mqtt_user, mqtt_password, topic_sub

client_id = ubinascii.hexlify(machine.unique_id())

def connect():
    #client = MQTTClient(client_id, mqtt_server)
    client = MQTTClient(client_id, mqtt_server, mqtt_port, mqtt_user, mqtt_password)
    client.connect()
    print('Connected to {} MQTT broker'.format(mqtt_server))
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Restarting in 10 seconds...')
    time.sleep(10)
    machine.reset()

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(wifi_ssid, wifi_password)

while station.isconnected() == False:
    pass

print('Connection successful', station.ifconfig())

try:
    ntptime.settime()
    print('Time updated: ' + utils.timestamp())
except Exception as e:
    ble.debug('ERROR: ntptime settime ' + str(e))

try:
    client = connect()
except OSError as e:
    restart_and_reconnect()

myBLE = ble.ble()
myBLE.setup()

print('Found:')
for a in myBLE.addresses:
    type, address, name = a
    ble.debug ('Found Address: {} Name: {}'.format(utils.prettify(address),name))


def cleanup():
    dir = uos.listdir()
    for f in dir:
        print(f)
        try:
            year = int(f[:4])
            month = int(f[4:6])
            mday = int(f[6:8])
            print(year, month, mday)
            filedate = time.mktime((year, month, mday, 0, 0, 0, 0, 0))
            year, month, mday, hour, minute, second, weekday, yearday = time.localtime()
            two_days_ago = time.mktime((year, month, mday-2, 0, 0, 0, 0, 0))
            print(filedate, two_days_ago)
            if filedate < two_days_ago:
                uos.remove(f)

        except Exception as e:
            print('ERROR: cleanup', str(e))
            pass


lastday = 0
while True:
    # update the RTC once a day
    today = utils.timestamp('day')
    if today != lastday:
        try:
            ntptime.settime()
            lastday = today
            ble.debug('Time set from server: ' + utils.timestamp())
        except Exception as e:
            ble.debug('ERROR: ntptime ' + str(e))

    # cleanup filesystem
    cleanup()

    # cycle through the captured addresses
    for a in myBLE.addresses:
        type, myBLE.address, name = a
        # if this is a 'LYWSD03MMC'
        if name == 'LYWSD03MMC':
            print('\r\n----------------------------------------------------------')
            # if we are successful reading the values
            if(myBLE.get_reading()):
                message = '{"temperature": "' + str(myBLE.temperature) + '", '
                message = message + '"humidity": "' + str(myBLE.humidity) + '", '
                message = message + '"batteryLevel": "' + str(myBLE.batteryLevel) + '", '
                message = message + '"batteryVoltage": "' + str(myBLE.voltage) + '"}'
                print(message)
                topic = topic_pub + '/' + ''.join('{:02x}'.format(b) for b in myBLE.address)
                print(topic)
                try:
                    client.publish(topic, message)
                except Exception as e:
                    ble.debug('ERROR: publish ' + str(e))
                    try:
                        client.disconnect()
                        client = connect()
                    except OSError as e:
                        restart_and_reconnect()

    # wait a minute for the next one
    time.sleep(60)

