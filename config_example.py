wifi_ssid = 'wifi_ssid'
wifi_password = 'wifi_password'
mqtt_server = '192.168.1.1'
mqtt_port = 1883
mqtt_user = 'mqtt_user'
mqtt_password = 'mqtt_password'
topic_pub = b'home/espble'

scan_for_devices = True
scan_interval = 21600 # Seconds
devices_list = [
    # Add your devices if you want them to be always loaded at startup,
    # without the need to discover them through BLE scan:
    # (<TYPE>, b'<MAC_ADDRESS>', '<NAME>')
]