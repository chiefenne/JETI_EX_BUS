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
import utime as time
import ustruct
from micropython import const

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

        # remember several values for the EX BUS
        self.start_altitude_saved = False
        self.start_altitude = 0
        self.last_altitude = 0
        self.last_climbrate = 0
        self.last_time = 0

        # initialize the EX BUS packet 
        # needed for check in ExBus.py, set to 'True' in main.py
        self.exbus_data_ready = False
        self.exbus_text1_ready = False
        self.exbus_text2_ready = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EX')

    def dummy(self):
        '''Dummy function for checking the lock.
        Stay locked for 5 seconds.'''
        self.logger.log('debug', 'core 1: EX, trying to acquire lock')
        start = time.ticks_us()
        self.lock.acquire()
        time.sleep_ms(5000)
        self.lock.release()
        end = time.ticks_us()
        diff = time.ticks_diff(end, start)
        self.logger.log('debug', 'core 1: EX, lock released after {} us'.format(diff))

    def Message(self):
        pass

    def Alarm(self, sensor):
        '''[summary]
        '''
        pass

    def exbus_frame(self, sensor, frametype='data',
                                  data_1=None,
                                  data_2=None,
                                  text=None):
        '''Prepare the EX BUS telemetry packet.
        It includes the EX packet and the EX BUS header.
        CRC16 is added later in ExBus.py as it needs to include the packet id.
        '''

        # get the sensor object
        self.current_sensor = sensor

        # setup ex packet
        self.ex_frame(sensor, frametype=frametype,
                              data_1=data_1,
                              data_2=data_2,
                              text=text)

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

        # checksum added later in ExBus.py as it needs to include the packet id

        return self.exbus_packet, self.ex_packet

    def ex_frame(self, sensor, frametype=None,
                               data_1=None,
                               data_2=None,
                               text=None):
        '''Compile the EX telemetry packet (Header, data or text, etc.).'''

        if frametype == 'data':
            # get sensor data
            data, length = self.Data(data_1=data_1, data_2=data_2)
        elif frametype == 'text':
            # get text data
            data, length = self.Text(text=text)

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
        header += self.sensors.productID
        header += self.sensors.deviceID

        # reserved (8th byte)
        header += b'\x00'

        return header

    def Data(self, data_1=None, data_2=None):
        '''EX data packet. This transfers two sensor values.'''

        self.data = bytearray()

        # FIXME: telemetry data are hardcoded for now
        # FIXME: telemetry data are hardcoded for now
        # FIXME: telemetry data are hardcoded for now

        # vario calculation
        current_time = time.ticks_ms()
        # use ticks_diff to produce correct result
        dt = time.ticks_diff(current_time, self.last_time)
        self.last_time = current_time
        altitude = self.current_sensor.altitude
        climbrate = (altitude - self.last_altitude) * (1000.0 / (dt + 1.e-9))
        smoothing = 0.85
        climbrate = climbrate + smoothing * (self.last_climbrate - climbrate)

        # compile 9th byte of EX data specification (2x 4bit)
        id1 = self.sensors.meta[data_1]['id'] << 4
        data_type = self.sensors.meta[data_1]['data_type']
        # combine bits for id and data type
        self.data += ustruct.pack('B', id1 | data_type)

        # data of 1st telemetry value, converted to EX format
        self.data += self.EncodeValue(climbrate,
                                      self.sensors.meta[data_1]['data_type'],
                                      self.sensors.meta[data_1]['precision'])

        # compile 11th+x byte of EX data specification (2x 4bit)
        id2 = self.sensors.meta[data_2]['id'] << 4
        data_type = self.sensors.meta[data_2]['data_type']

        # combine bits for id and data type
        self.data += ustruct.pack('B', id2 | data_type)
        
        # data of 2nd telemetry value, converted to EX format
        self.data += self.EncodeValue(altitude - self.start_altitude,
                                      self.sensors.meta[data_2]['data_type'],
                                      self.sensors.meta[data_2]['precision'])

        # store start altitude
        if not self.start_altitude_saved:
            self.start_altitude = altitude
            self.start_altitude_saved = True

        # store data for next iteration
        self.last_altitude = altitude
        self.last_climbrate = climbrate

        return self.data, len(self.data)

    def Text(self, frametype='text', text=None):
        '''EX text packet. This transfers the sensor description and unit for
        one sensor value. Two text packets are needed to transfer the
        description and unit for one data packet (as it sends two values).
        '''

        self.text = bytearray()
        # compile 9th byte of EX text specification (1 byte)
        id = self.sensors.meta[text]['id']
        self.text += ustruct.pack('B', id)

        # compile 10th byte of EX text specification (5bits + 3bits)
        len_description = len(self.sensors.meta[text]['description'])
        len_unit = len(self.sensors.meta[text]['unit'])
        self.text += ustruct.pack('B', len_description << 3 | len_unit)

        # compile 11th+x bytes of EX text specification
        description = self.sensors.meta[text]['description']
        for c in description:
            self.text += bytes([ord(c)])

        # compile 11+x+y bytes of EX text specification (y bytes)
        unit = self.sensors.meta[text]['unit']
        for c in unit:
            self.text += bytes([ord(c)])

        return self.text, len(self.text)

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
        '''Encode telemetry value.
        
        Data type | Description |  Note
        ----------|-------------|---------------------------------------
            0     |   int6_t    |  Data type  6b (-31 ,31)
            1     |   int14_t   |  Data type 14b (-8191 ,8191)
            4     |   int22_t   |  Data type 22b (-2097151 ,2097151)
            5     |   int22_t   |  Data type 22b (-2097151 ,2097151)
            8     |   int30_t   |  Data type 30b (-536870911 ,536870911)
            9     |   int30_t   |  Data type 30b (-536870911 ,536870911)
        '''

        # FIXME: check if all formats are working
        # FIXME: check if all formats are working
        # FIXME: check if all formats are working

        # format for pack
        # fmt = {0: '<B', 1: '<H', 4: '<I', 5: '<I', 8: '<L', 9: '<L'} # unsigned
        fmt = {0: '<b', 1: '<h', 4: '<i', 5: '<i', 8: '<l', 9: '<l'} # signed

        # number of bytes needed to encode the value
        bytes_for_datatype = {0: 1, 1: 2, 4: 3, 5: 3, 8: 4, 9: 4}

        # number of bytes needed to encode the value
        num_bytes = bytes_for_datatype[dataType]

        # get the bit for the sign
        sign = 0x01 if value < 0 else 0x00
        mult = -1 if value < 0 else 1

        # scale value based on precision and round it
        value_scaled = int(value * 10**precision + mult * 0.5)

        # check that zero is positive; otherwise wrong value is encoded
        if value_scaled == 0:
            sign = 0x00

        # combine sign, precision and scaled value
        lo_byte = value_scaled & 0xFF
        hi_byte = ((value_scaled >> 8) & 0x1F) | (sign << 7) | (precision << 5)

        # encode the value
        value_ex = ustruct.pack('bb', lo_byte, hi_byte)

        # self.logger.log('debug',
        #                 'Encoding value: {}, scaled: {}, sign: {}, lo: {}, hi: {}'.
        #                 format(value, value_scaled, sign, lo_byte, hi_byte))

        # return the encoded value as bytes in little endian format
        return value_ex

    def lowpass_iir_filter(input_signal, cutoff_frequency, sample_rate):
        '''Lowpass infinite impulse response filter (IIR).'''

        output_signal = [0] * len(input_signal)
        alpha = (2 * 3.14159 * cutoff_frequency) / sample_rate
        a = 1 - alpha

        output_signal[0] = input_signal[0]

        for i in range(1, len(input_signal)):
            output_signal[i] = alpha * input_signal[i] + a * output_signal[i - 1]

        return output_signal
