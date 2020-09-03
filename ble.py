from ubluetooth import BLE, UUID, FLAG_NOTIFY, FLAG_READ, FLAG_WRITE
from micropython import const
import utime as time
from binascii import unhexlify
import array
import micropython
import utils
import logging, logger
logger.initLogging()

micropython.alloc_emergency_exception_buf(100)

_IRQ_CENTRAL_CONNECT                 = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT              = const(1 << 1)
_IRQ_GATTS_WRITE                     = const(1 << 2)
_IRQ_GATTS_READ_REQUEST              = const(1 << 3)
_IRQ_SCAN_RESULT                     = const(1 << 4)
_IRQ_SCAN_COMPLETE                   = const(1 << 5)
_IRQ_PERIPHERAL_CONNECT              = const(1 << 6)
_IRQ_PERIPHERAL_DISCONNECT           = const(1 << 7)
_IRQ_GATTC_SERVICE_RESULT            = const(1 << 8)
_IRQ_GATTC_CHARACTERISTIC_RESULT     = const(1 << 9)
_IRQ_GATTC_DESCRIPTOR_RESULT         = const(1 << 10)
_IRQ_GATTC_READ_RESULT               = const(1 << 11)
_IRQ_GATTC_WRITE_STATUS              = const(1 << 12)
_IRQ_GATTC_NOTIFY                    = const(1 << 13)
_IRQ_GATTC_INDICATE                  = const(1 << 14)
_ARRAYSIZE = const(20)


class ble:
    def __init__(self):
        logging.info("Initializing BLE...")
        self.bt = BLE()
        self.bt.irq(handler=self.bt_irq)
        logging.info('Waiting to set BLE active...')
        self.bt.active(True)

        self.addresses=[]
        for i in range (_ARRAYSIZE):
            self.addresses.append((100, b'AAAAAA','name'))
        self.conn_handle = 0
        self.connected = False
        self.write_flag = False
        self.read_flag = False
        self.notify = False
        self.index = 0
        self.scan_complete = False
        self.notify_data = bytearray(30)
        self.address = bytearray(6)
        self.char_data = bytearray(30)
        self.temperature = 0
        self.humidity = 0
        self.battery_voltage = 0
        self.battery_level = 0


    def setup(self):
        # Start device scan
        self.scan_devices()
        # Perform a scan to identify all the devices
        self.identify_devices()


    def scan_devices(self):
        self.scan_complete = False
        self.index = 0
        logging.info('Starting scan...')
        # Run a scan operation lasting for the specified duration (in milliseconds).
        # Use interval_us and window_us to optionally configure the duty cycle.
        # The scanner will run for window_us microseconds every interval_us microseconds for a total of duration_ms milliseconds.
        # The default interval and window are 1.28 seconds and 11.25 milliseconds respectively (background scanning).
        #
        # Scan for 60s (at 100% duty cycle)
        duration_ms = 60000 # milliseconds
        interval_us = 30000 # microseconds
        window_us   = 30000 # microseconds
        try:
            self.bt.gap_scan(duration_ms, interval_us, window_us)
        except Exception as e:
            utils.log_error_to_file('ERROR: scan - ' + str(e))
            
        while not self.scan_complete:
            pass


    def identify_devices(self):
        for i in range(len(self.addresses)):
            self.type, self.address, self.name = self.addresses[i]
            if self.type < 100:
                self.get_name(i)
                logging.debug('Name: {}', self.name)
                if self.name != 'name':
                    self.addresses[i] = (self.type, self.address, self.name)
                time.sleep(1)
            else:
                self.addresses = self.addresses[:i]            # truncate self.addresses
                break


    def get_name(self, i):
        print('\r\n--------------------------------------------')
        logging.debug('Type: {} - Address: {}', self.type, utils.prettify(self.address))
        if self.connect():
            time.sleep(1)
            if (self.read_data(0x0003)):
                try:
                    self.name = self.char_data.decode("utf-8")
                    self.name = self.name[:self.name.find('\x00')]  # drop trailing zeroes
                    logging.debug('Name: {} - Length: {}', self.name, len(self.name))
                except Exception as e:
                    utils.log_error_to_file('ERROR: setup - ' + str(e))

                logging.info('Got {}', self.name )
            self.disconnect()


    def connect(self, type=0):
        # Connect to the device at self.address
        count = 0
        # Loop until connection successful
        while not self.connected:
            logging.info('Trying to connect to {}...', utils.prettify(self.address))
            try:
                conn = self.bt.gap_connect(type, self.address)
            except Exception as e:
                utils.log_error_to_file('ERROR: connect - ' + str(e))

            time.sleep(1)
            count += 1
            if count > 60:
                return False
        return True


    def disconnect(self):
        logging.info('Disconnecting...')
        try:
            conn = self.bt.gap_disconnect(self.conn_handle)
        except Exception as e:
            utils.log_error_to_file('ERROR: disconnect - ' + str(e))

        # Returns false on timeout
        timer = 0
        while self.connected:
            # print('.', end='')
            time.sleep(1)
            timer += 1
            if timer > 60:
                return False
        return True


    def read_data(self, value_handle):
        self.read_flag = False

        logging.info('Reading data...')
        try:
            self.bt.gattc_read(self.conn_handle, value_handle)
        except Exception as e:
            utils.log_error_to_file('ERROR: read - ' + str(e))
            return False

        # Returns false on timeout
        timer = 0
        while not self.read_flag:
            # print('.', end='')
            time.sleep(1)
            timer += 1
            if timer > 60:
                return False
        return True


    def write_data(self, value_handle, data):
        self.write_flag = False

        # Checking for connection before write
        self.connect()
        logging.info('Writing data...')
        try:
            self.bt.gattc_write(self.conn_handle, value_handle, data, 1)
        except Exception as e:
            utils.log_error_to_file('ERROR: write - ' + str(e))
            return False

        # Returns false on timeout
        timer = 0
        while not self.write_flag:
            # print('.', end='')
            time.sleep(1)
            timer += 1
            if timer > 60:
                return False
        return True


    def get_reading(self):
        self.connect()

        # Enable notifications of Temperature, Humidity and Battery voltage
        logging.info('Enabling notifications for data readings...')
        data = b'\x01\x00'
        value_handle = 0x0038
        if (self.write_data(value_handle, data)):
            logging.info('Write successful')
        else:
            logging.warning('Write failed')

        # Enable energy saving
        logging.info('Enabling energy saving...')
        data = b'\xf4\x01\x00'
        value_handle = 0x0046
        if (self.write_data(value_handle, data)):
            logging.info('Write successful')
        else:
            logging.warning('Write failed')

        # Wait for a notification
        logging.info('Waiting for a notification...')
        self.notify = False
        timer = 0
        while not self.notify:
            # print('.', end='')
            time.sleep(1)
            timer += 1
            if timer > 60:
                self.disconnect()
                return False

        logging.info('Data received!')
        self.temperature = int.from_bytes(self.notify_data[0:2], 'little') / 100
        self.humidity = int.from_bytes(self.notify_data[2:3], 'little')
        self.battery_voltage = int.from_bytes(self.notify_data[3:5], 'little') / 1000
        self.battery_level = min(int(round((self.battery_voltage - 2.1), 2) * 100), 100) # 3.1 or above --> 100% 2.1 --> 0 %
        self.disconnect()
        return True


    # Bluetooth Interrupt Handler
    def bt_irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            # A single scan result.
            addr_type, addr, connectable, rssi, adv_data = data
            if addr_type == 0:
                logging.debug('Address type: {} - Address: {}', addr_type, utils.prettify(addr))
                if (addr_type, bytes(addr), 'name') not in self.addresses:
                    self.addresses[self.index] = (addr_type, bytes(addr), 'name')
                    self.index += 1
                
        elif event == _IRQ_SCAN_COMPLETE:
            # Scan duration finished or manually stopped.
            logging.info('Scan complete')
            self.scan_complete = True
            
        elif event == _IRQ_PERIPHERAL_CONNECT:
            logging.debug('IRQ peripheral connect')
            self.conn_handle, _, _, = data
            self.connected = True
            
        if event == _IRQ_CENTRAL_CONNECT:
            # A central has connected to this peripheral.
            self.conn_handle, addr_type, addr = data
            logging.debug('A central has connected to this peripheral.')
            logging.debug('Connection handle: {} - Address type: {} - Address: {}', self.conn_handle, addr_type, addr)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            # A central has disconnected from this peripheral.
            self.conn_handle, addr_type, addr = data
            logging.debug('A central has disconnected from this peripheral.')
            logging.debug('Connection handle: {} - Address type: {} - Address: {}', self.conn_handle, addr_type, addr)

        elif event == _IRQ_GATTS_WRITE:
            # A central has written to this characteristic or descriptor.
            self.conn_handle, attr_handle = data
            logging.debug('A central has written to this characteristic or descriptor.')
            logging.debug('Connection handle: {} - Attribute handle: {}', self.conn_handle, attr_handle)

        elif event == _IRQ_GATTS_READ_REQUEST:
            # A central has issued a read. Note: this is a hard IRQ.
            # Return None to deny the read.
            # Note: This event is not supported on ESP32.
            self.conn_handle, attr_handle = data
            
        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Connected peripheral has disconnected.
            self.conn_handle, addr_type, addr = data
            logging.debug('Connected peripheral has disconnected.')
            logging.debug('Connection handle: {} - Address type: {} - Address: {}', self.conn_handle, addr_type, utils.prettify(addr))
            self.connected = False
            # print('Set connect flag', self.connected)
            
        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Called for each service found by gattc_discover_services().
            self.conn_handle, start_handle, end_handle, uuid = data
            logging.debug('Called for each service found by gattc_discover_services().')
            logging.debug('Connection handle: {} - Start handle: {} - End handle: {} - UUID: {}', self.conn_handle, start_handle, end_handle, uuid)

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Called for each characteristic found by gattc_discover_services().
            self.conn_handle, def_handle, value_handle, properties, uuid = data
            logging.debug('Called for each characteristic found by gattc_discover_services().')
            logging.debug('Connection handle: {} - Def handle: {} - Value handle: {} - Properties: {} - UUID: {}', self.conn_handle, def_handle, value_handle, properties, uuid)
            # print('Value handle {:02x}'.format(value_handle))
            # characteristics[self.index] = value_handle
            # self.index += 1
            
        elif event == _IRQ_GATTC_DESCRIPTOR_RESULT:
            # Called for each descriptor found by gattc_discover_descriptors().
            conn_handle, dsc_handle, uuid = data
            logging.debug('Called for each descriptor found by gattc_discover_descriptors().')
            logging.debug('Connection handle: {} - Dsc handle: {} - UUID: {}', conn_handle, dsc_handle, uuid)

        elif event == _IRQ_GATTC_READ_RESULT:
            # A gattc_read() has completed.
            conn_handle, value_handle, char_data = data
            logging.debug('A gattc_read() has completed.')
            logging.debug('Connection handle: {} - Value handle: {} - Char data: {}', conn_handle, value_handle, char_data)

            for b in range(len(char_data)):
                self.char_data[b] = char_data[b]
                
            self.read_flag = True

        elif event == _IRQ_GATTC_WRITE_STATUS:
            # A gattc_write() has completed.
            self.conn_handle, value_handle, status = data
            logging.debug('A gattc_write() has completed - status.')
            logging.debug('Connection handle: {} - Value handle: {} - Status: {}', self.conn_handle, value_handle, status)
            self.write_flag = True
            
        elif event == _IRQ_GATTC_NOTIFY:
            # A peripheral has sent a notify request.
            self.conn_handle, value_handle, notify_data = data
            logging.debug('A peripheral has sent a notify request.')
            logging.debug('Connection handle: {} - Value handle: {} - Notify data: {}', self.conn_handle, value_handle, notify_data)
            for b in range(len(notify_data)):
                self.notify_data[b] = notify_data[b]
            
            self.notify = True
            
        elif event == _IRQ_GATTC_INDICATE:
            # A peripheral has sent an indicate request.
            self.conn_handle, value_handle, self.notify_data = data
            logging.debug('A peripheral has sent an indicate request.')
            logging.debug('Connection handle: {} - Value handle: {} - Notify data: {}', self.conn_handle, value_handle, self.notify_data)
