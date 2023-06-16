'''Python Implementation of the JETI EX protocol

This protocol describes how data, text, messages and alarms are sent to
and from the Jeti receiver.

The EX protocol is used in two ways:
  - In older Jeti devices at lower communication speed (9600-9800 baud)
  - As part of the newer "EX Bus" protocol (125 or 250kbaud)

In both cases it carries the telemetry data (data, text, message, alarms).


Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

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


class Ex:
    '''Jeti EX protocol handler. 
    '''

    def __init__(self, sensors, lock):

        # list of sensors
        self.sensors = sensors

        # lock object used to prevent other cores from accessing shared resources
        self.lock = lock

        # initialize the EX BUS packet 
        # needed for check in ExBus.py, set to 'True' in main.py
        self.exbus_data_ready = False
        self.exbus_text_ready = False
        self.exbus_device_ready = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EX')

    def dummy(self):
        '''Dummy function for checking the lock.
        Stay locked for 5 seconds.'''
        self.logger.log('debug', 'core 1: EX, trying to acquire lock')
        start = utime.ticks_us()
        self.lock.acquire()
        utime.sleep_ms(5000)
        self.lock.release()
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
        self.ex_frame(sensor, frametype=frametype)

        # initiliaze the EX BUS packet
        self.exbus_packet = bytearray()

        # EX bus header
        self.exbus_packet += b'\x3B\x01'

        # EX bus packet length in bytes including the header and CRC
        self.exbus_packet += ustruct.pack('B', len(self.ex_packet) + 8)
        
        # put dummy id here; will be replaced by packet id later
        self.exbus_packet += b'\x00'

        # telemetry identifier
        self.exbus_packet += b'\x3A'

        # complete EX packet length (including 0xF and crc8 bytes)
        self.exbus_packet += ustruct.pack('B', len(self.ex_packet))

        # add EX packet
        self.exbus_packet += self.ex_packet

        # checksum added in ExBus.py as it needs to include the packet id
        # checksum added in ExBus.py as it needs to include the packet id
        # checksum added in ExBus.py as it needs to include the packet id

        return self.exbus_packet, self.ex_packet

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
            data, length = self.DeviceName()

        # compile header (types are 'text', 'data', 'message')
        header = self.Header(frametype, length)

        # compile the complete EX packet
        self.ex_packet = bytearray()
        self.ex_packet += header
        self.ex_packet += data

        # crc for telemetry (8-bit crc)
        # counting begins at the length byte of a message (skipping the header)
        crc8, crc8_int = CRC8.crc8(self.ex_packet[1:])

        # add crc8 to the packet ('B' is unsigned byte 8-bit)
        self.ex_packet += ustruct.pack('B', crc8_int)

        # self.logger.log('debug', 'self.ex_packet: {}'.format(self.ex_packet))
        # self.logger.log('debug', 'crc8: {}'.format(ustruct.pack('B', crc8_int)))

        # compile simple text protocol
        # message = 'A simple text message'
        # simple_text = self.SimpleText(message)
        # add simple text (34 bytes)
        # self.ex_packet += simple_text

        return self.ex_packet

    def Header(self, frametype, length):
        '''EX packet message header.'''

        header = bytearray()

        ex_types = {'text': 0, 'data': 1, 'message': 2, 'device': 0}

        # message separator - not needed if EX frame is embedded in EX BUS frame
        # header += b'\x7E'

        # packet identifier
        header += b'\x0F'

        # 2 bits for packet type (0=text, 1=data, 2=message)
        # these are the two leftmost bits of 3rd byte; shift left by 6
        telemetry_type = ex_types[frametype] << 6

        # telemetry_length (+4 for serial number,
        #                   +1 is for reserved 8th byte)
        #                   +1 is for crc8 byte)
        telemetry_length = length + 4 + 1 + 1

        # combine 2+6 bits (3rd byte)
        type_length = telemetry_type | telemetry_length
        header += ustruct.pack('B', type_length)

        # serial number (bytes 4-5 and 6-7)
        # combine productID and deviceID (2 bytes), LSB first, MSB last
        productID = self.sensors.productID
        deviceID = ustruct.pack('B', self.current_sensor.deviceID) + b'\x00'
        header += productID
        header += deviceID

        # reserved (8th byte)
        header += b'\x00'

        return header

    def Data(self):
        '''EX packet data.'''

        self.data = bytearray()

        # FIXME: will be refactored to automatically loop through all sensors
        # FIXME: will be refactored to automatically loop through all sensors
        # FIXME: will be refactored to automatically loop through all sensors

        if self.current_sensor._type == 'pressure':

            # compile 9th byte of EX data specification (2x 4bit)
            id = self.sensors.ID_PRESSURE << 4
            data_type = self.sensors.meta['ID_PRESSURE']['data_type']

            # combine bits for id and data type
            self.data += ustruct.pack('B', id | data_type)

            # data of 1st telemetry value, converted to EX format
            val = self.EncodeValue(self.current_sensor.pressure,
                                   self.sensors.meta['ID_PRESSURE']['data_type'],
                                   self.sensors.meta['ID_PRESSURE']['precision'])
            self.data += val

            # compile 11th+x byte of EX data specification (2x 4bit)
            id = self.sensors.ID_TEMP << 4
            data_type = self.sensors.meta['ID_TEMP']['data_type']

            # combine bits for id and data type
            self.data += ustruct.pack('B', id | data_type)
                                         
            # data of 2nd telemetry value, converted to EX format
            val = self.EncodeValue(self.current_sensor.temperature,
                                   self.sensors.meta['ID_TEMP']['data_type'],
                                   self.sensors.meta['ID_TEMP']['precision'])
            self.data += val

        return self.data, len(self.data)

    def Text(self):
        '''EX packet text.'''

        if self.current_sensor._type == 'pressure':

            self.text = bytearray()
            # compile 9th byte of EX text specification (1 byte)
            id = self.sensors.ID_PRESSURE
            self.text += ustruct.pack('B', id)

            # compile 10th byte of EX text specification (5bits + 3bits)
            len_description = len(self.sensors.meta['ID_PRESSURE']['description'])
            len_unit = len(self.sensors.meta['ID_PRESSURE']['unit'])
            self.text += ustruct.pack('B', len_description << 3 | len_unit)

            # compile 11th+x bytes of EX text specification
            description = self.sensors.meta['ID_PRESSURE']['description']
            for c in description:
                self.text += bytes([ord(c)])

            # compile 11+x+y bytes of EX text specification (y bytes)
            unit = self.sensors.meta['ID_PRESSURE']['unit']
            for c in unit:
                self.text += bytes([ord(c)])

        return self.text, len(self.text)

    def DeviceName(self):
        '''Name of the device.'''
        
        # FIXME: this function will be integrated into the Text() function
        # FIXME: this function will be integrated into the Text() function
        # FIXME: this function will be integrated into the Text() function
        
        self.device = bytearray()
        
        # The zero-valued identifier is reserved for the device name
        # compile 9th byte of EX text specification (1 byte)
        id = self.sensors.ID_DEVICE
        self.device += ustruct.pack('B', id)

        # compile 10th byte of EX text specification (5bits + 3bits)
        len_description = len(self.sensors.meta['ID_DEVICE']['description'])
        len_unit = len(self.sensors.meta['ID_DEVICE']['unit'])
        self.device += ustruct.pack('B', len_description << 3 | len_unit)

        # compile 11th byte of EX text specification (x bytes)
        description = self.sensors.meta['ID_DEVICE']['description']
        for c in description:
            self.device += bytes([ord(c)])

        # compile 11+x byte of EX text specification (y bytes)
        unit = self.sensors.meta['ID_DEVICE']['unit']
        for c in unit:
            self.device += bytes([ord(c)])

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
        for c in text:
            self.simple_text += bytes([ord(c)])

        # separator of message (end)
        self.simple_text += b'FF'

        return self.simple_text

    def EncodeValue(self, value, dataType, precision):
        '''Encode telemetry value.'''

        value_enc = list()

        # scale value based on precision
        value = int(value * 10**precision)

        if dataType ==  0: # TYPE_6b
            value_enc.append((value & 0x1F) | (0x80 if value < 0 else 0x00))
            value_enc[0] |= precision

        elif dataType == 1: # TYPE_14b
            value_enc.append(value & 0xFF)
            value_enc.append(((value >> 8) & 0x1F) | (0x80 if value < 0 else 0x00))
            value_enc[1] |= precision

        elif dataType == 4: # TYPE_22b
            value_enc.append(value & 0xFF)
            value_enc.append((value >> 8) & 0xFF)
            value_enc.append(((value >> 16) & 0x1F) | (0x80 if value < 0 else 0x00))
            value_enc[2] |= precision

        elif dataType == 5: # time and date
            value_enc.append(value & 0xFF)
            value_enc.append((value >> 8) & 0xFF)
            value_enc.append(((value >> 16) & 0xFF) | (0x80 if value < 0 else 0x00))

        elif dataType == 8: # TYPE_30b
            value_enc.append(value & 0xFF)
            value_enc.append((value >> 8) & 0xFF)
            value_enc.append((value >> 16) & 0xFF)
            value_enc.append(((value >> 24) & 0x1F) | (0x80 if value < 0 else 0x00))
            value_enc[3] |= precision

        elif dataType == 9: # GPS coordinates
            value_enc.append(value & 0xFF)
            value_enc.append((value >> 8) & 0xFF)
            value_enc.append((value >> 16) & 0xFF)
            value_enc.append((value >> 24) & 0xFF)

        # convert list of integers to bytes in a bytearray
        value_encoded = bytearray()
        for v in value_enc:
            value_encoded += ustruct.pack('B', v)

        return value_encoded
