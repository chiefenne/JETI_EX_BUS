'''Python Implementation of the JETI EX protocol

This protocol describes how data, text, messages and alarms are sent to
and from the Jeti receiver.

The EX protocol is used in two ways:
  - In older Jeti devices at lower communication speed (9600-9800 baud)
  - As part of the newer "EX Bus" protocol (125 or 250kbaud)

In both cases it carries the telemetry data (data, text, message, alarms).

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from ubinascii import hexlify, unhexlify
import ujson
import utime
import ustruct

from Jeti import CRC8
from Jeti import CRC16
from Utils.Logger import Logger
import Utils.lock as lock


class Ex:
    '''Jeti EX protocol handler. 
    '''

    def __init__(self, sensors):

        # list of sensors
        self.sensors = sensors

        # initialize the EX BUS packet (needed for check in ExBus.py)
        self.exbus_ready = None

        # initialize the device name
        self.DeviceName()

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EX')

    def lock(self):
        '''Lock EX protocol for exclusive access'''

        lock.lock.acquire()

    def release(self):
        '''Release EX protocol'''

        lock.lock.release()

    def dummy(self):
        '''Dummy function for checking the lock.
        Stay locked for 5 seconds.'''
        self.logger.log('debug', 'core 1: EX, trying to acquire lock')
        start = utime.ticks_us()
        self.lock()
        self.release()
        end = utime.ticks_us()
        diff = utime.ticks_diff(end, start)
        self.logger.log('debug', 'core 1: EX, lock released after {} us'.format(diff))

    def Message(self):
        pass

    def Alarm(self, sensor):
        '''[summary]
        '''
        pass

    def exbus_frame(self, sensor, frametype='data'):
        '''Prepare the EX BUS telemetry packet.
        It includes the EX packet and the EX BUS header and CRC.
        '''

        # setup ex packet
        self.ex_packet = self.ex_frame(sensor, frametype=frametype)

        self.exbus_packet = bytearray()

        # EX bus header
        self.exbus_packet += b'\x3B\x01'

        # EX bus packet length in bytes including the header and CRC
        self.exbus_packet += ustruct.pack('b', len(self.ex_packet) + 8)
        
        # put dummy id here; will be replaced by packet id later
        self.exbus_packet += b'\x00'

        # telemetry identifier
        self.exbus_packet += b'\x3A'

        # packet length in bytes of EX packet
        self.exbus_packet += ustruct.pack('b', len(self.ex_packet))

        # add EX packet
        self.exbus_packet += self.ex_packet

        # calculate the crc for the packet
        crc = CRC16.crc16_ccitt(self.exbus_packet)

        # swap bytes (LSB and MSB)
        self.exbus_packet += crc[2:]
        self.exbus_packet += crc[:2]

        return self.exbus_packet

    def ex_frame(self, sensor, frametype='data'):
        '''Compile the EX telemetry packet (Header, data or text, etc.).'''
        self.current_sensor = sensor

        if frametype == 'data':
            # get sensor data
            data, length = self.Data()
        elif frametype == 'text':
            # get text data
            data, length = self.Text()
        elif frametype == 'device':
            # get device name
            data, length = self.Device()

        # compile header (types are 'text', 'data', 'message')
        header = self.Header(frametype, length)

        # compile simple text protocol
        message = 'A simple text message'
        simple_text = self.SimpleText(message)

        # compile the complete EX packet
        self.ex_packet = bytearray()
        self.ex_packet += header
        self.ex_packet += data

        # crc for telemetry (8-bit crc); checksum begins at 3rd byte
        # here we use take the 2nd byte (length) into account
        # because we do not use the separator byte (0x7E)
        crc8 = CRC8.crc8(self.ex_packet[1:])
        self.ex_packet += crc8

        # add simple text (34 bytes)
        self.ex_packet += simple_text

        return self.ex_packet

    def Header(self, frametype, length):
        '''EX packet message header.'''

        header = bytearray()

        types = {'text': 0, 'data': 1, 'message': 2}

        # message separator - not needed if EX frame is embedded in EX BUS frame
        # header += b'\x7E'

        # packet identifier
        header += b'\x0F'

        # 2 bits for packet type (0=text, 1=data, 2=message)
        # these are the two leftmost bits of 3rd byte; shift left by 6
        telemetry_type = types[frametype] << 6

        # telemetry_length (+1 is for the crc8 byte)
        telemetry_length = length + 1

        # combine 2+6 bits (3rd byte)
        type_length = telemetry_type | telemetry_length
        header += ustruct.pack('b', type_length)

        # serial number (bytes 4-5 and 6-7)
        # combine productID and deviceID (2 bytes), LSB first, MSB last
        productID = self.sensors.productID
        deviceID = ustruct.pack('b', self.current_sensor.deviceID) + b'\x00'
        header += productID
        header += deviceID

        # reserved (8th byte)
        header += b'\x00'

        return header

    def Data(self):
        '''EX packet data.'''

        self.data = bytearray()


        if self.current_sensor._type == 'pressure':

            # compile 9th byte of EX data specification (2x 4bit)
            # 1st 4bit (from left): sensor id, 2nd 4bit: data type
            id = self.sensors.ID_PRESSURE << 4
            data_type = self.sensors.meta['ID_PRESSURE']['data_type']

            # combine bits for id and data type
            # convert int to bytes (e.g. 20 --> b'\x14')
            self.data += ustruct.pack('b', id | data_type)

            # data of 1st telemetry value
            nbytes = self.sensors.meta['ID_PRESSURE']['bytes']
            precision = self.sensors.meta['ID_PRESSURE']['precision']
            value = self.current_sensor.pressure
            sign = 0 if value >= 0x0 else 1
            scaled_value = int(value * 10**precision)

            # convert value to EX format
            val = sign << (nbytes*8 - 1) | precision << (nbytes*8 - 3) | scaled_value

            # append data to packet as bytes
            self.data += ustruct.pack('b', val)

            # compile 11th+x byte of EX data specification (2x 4bit)
            id = self.sensors.ID_TEMP << 4
            data_type = self.sensors.meta['ID_TEMP']['data_type']

            # combine bits for id and data type
            # convert int to bytes (e.g. 20 --> b'\x14')
            self.data += ustruct.pack('b', id | data_type)
                                         
            # data of 2nd telemetry value
            nbytes = self.sensors.meta['ID_TEMP']['bytes']
            precision = self.sensors.meta['ID_TEMP']['bytes']
            value = self.current_sensor.temperature
            sign = 0 if value >= 0x0 else 1
            scaled_value = int(value * 10**precision)

            # convert value to EX format
            val = sign << (nbytes*8 - 1) | precision << (nbytes*8 - 3) | scaled_value

            # append data to packet as bytes
            self.data += ustruct.pack('b', val)

        return self.data, len(self.data)

    def Text(self):
        '''EX packet text.'''

        if self.current_sensor._type == 'pressure':

            self.text = bytearray()
            # compile 9th byte of EX text specification (1 byte)
            id = self.sensors.ID_PRESSURE
            self.text += ustruct.pack('b', id)

            # compile 10th byte of EX text specification (5bits + 3bits)
            len_description = len(self.sensors.meta['ID_PRESSURE']['description'])
            len_unit = len(self.sensors.meta['ID_PRESSURE']['unit'])

            self.text += ustruct.pack('b', len_description << 3 | len_unit)

            # compile 11th byte of EX text specification (x bytes)
            description = self.sensors.meta['ID_PRESSURE']['description']
            self.text += hexlify(description.encode('utf-8'))

            # compile 11+x byte of EX text specification (y bytes)
            unit = self.sensors.meta['ID_PRESSURE']['unit']
            self.text += hexlify(unit.encode('utf-8'))

        return self.text, len(self.text)

    def DeviceName(self):
        '''Name of the device.'''
        self.device = bytearray()
        # The zero-valued identifier is reserved for the device name.
        self.device += ustruct.pack('b', 0)
        # device name
        devicename = 'MHBvario'
        # length of the device name
        self.device += ustruct.pack('b', len(devicename))
        # length of the unit's description (here no unit, thus 0)
        self.device += ustruct.pack('b', 0)
        # The device name is a string of up to ?? characters.
        self.device += hexlify(devicename.encode('utf-8'))
        # The unit's description (here no unit)
        self.device += hexlify(''.encode('utf-8'))

        return self.device, len(self.device)

    def Message(self):
        '''EX packet message.'''

        pass

    def Alarm(self):
        '''EX packet alarm.'''
        pass

    def SimpleText(self, text):
        '''EX packet simple text (must be 34 bytes long).
        32 bytes of text are needed + 2 bytes for the separators.
        The simple text is concatenated to every telemetry packet.
        '''

        # crop text if too long, fill up if needed, left adjusted
        # 32 bytes are reserved for the text
        text = '{:<32}'.format(text[:32])

        self.simple_text = bytearray()

        # separator of message (begin)
        self.simple_text += b'\xFE'

        # add the text to the packet
        self.simple_text += hexlify(text.encode('utf-8'))

        # separator of message (end)
        self.simple_text += b'FF'

        return self.simple_text
