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
from Utils.round_robin import cycler
from Utils import status, fir_py
from Utils.moving_average import MovingAverageFilter


class Ex:
    '''Jeti EX protocol handler. 
    '''

    def __init__(self, sensors, lock):

        # list of sensors
        self.sensors = sensors

        # lock object used to prevent other cores from accessing shared resources
        self.lock = lock

        # remember values for the variometer
        self.last_altitude = 0
        self.last_climbrate = 0
        self.vario_time_old = time.ticks_ms()
        self.vario_smoothing = const(0.85)
        self.deadzone = 0.05

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

    def run_forever(self):
        '''Run the EX protocol forever.
        The EX BUS protocol is also prepared here.
        '''

        # make a generator out of the list of sensors
        cycle_sensors = cycler(self.sensors.get_sensors())

        #
        device_sent = False
        self.exbus_device_ready = False
        self.exbus_data_ready = False
        self.exbus_text1_ready = False
        self.exbus_text2_ready = False

        while status.main_thread_running:

            # cycle infinitely through all sensors
            self.current_sensor = next(cycle_sensors)

            # collect data from currently selected sensor
            # the "read_jeti" method must be implemented sensor specific
            # see Sensors/bme280_i2c.py
            self.current_sensor.read_jeti()

            self.lock.acquire()

            # update data frame (new sensor data)
            # 2 values per data frame, 1 value per text frame (so 2 text frames per data frame)
            # FIXME: data are hardcoded for testing purposes
            # FIXME: data are hardcoded for testing purposes
            # FIXME: data are hardcoded for testing purposes
            telemetry_1 = 'CLIMB'
            telemetry_2 = 'REL_ALTITUDE'

            if device_sent:
                self.exbus_data, _ = self.exbus_frame(frametype='data',
                                                      data_1=telemetry_1,
                                                      data_2=telemetry_2)
                self.exbus_text1, _ = self.exbus_frame(frametype='text',
                                                       text=telemetry_1)
                self.exbus_text2, _ = self.exbus_frame(frametype='text',
                                                       text=telemetry_2)

                self.exbus_data_ready = True
                self.exbus_text1_ready = True
                self.exbus_text2_ready = True
            else:
                # send the device name first
                self.exbus_device, _ = self.exbus_frame(frametype='text',
                                                        text='DEVICE')
                self.exbus_device_ready = True
                device_sent = True
                self.logger.log('info', 'DEVICE information prepared')
                self.logger.log('info', 'Starting EX BUS telemetry')

            self.lock.release()

        return

    def exbus_frame(self, frametype='data',
                                  data_1=None,
                                  data_2=None,
                                  text=None,
                                  msg_class=None):
        '''Prepare the EX BUS telemetry packet.
        It includes the EX packet and the EX BUS header.
        CRC16 is added later in ExBus.py as it needs to include the packet id.
        '''

        # setup ex packet
        ex_packet, len_ex = self.ex_frame(frametype=frametype,
                                          data_1=data_1,
                                          data_2=data_2,
                                          text=text,
                                          msg_class=msg_class)

        # initiliaze the EX BUS packet
        exbus_packet = bytearray()

        # EX bus header
        exbus_packet += b'\x3B\x01'

        # EX bus packet length in bytes including the header and CRC
        exbus_packet += ustruct.pack('B', len_ex + 8)
        
        # put dummy id here; will be replaced by packet id later
        exbus_packet += b'\x00'

        # telemetry identifier
        exbus_packet += b'\x3A'

        # EX packet length (including 0xF and crc8 bytes)
        exbus_packet += ustruct.pack('B', len_ex)

        # add EX packet
        exbus_packet += ex_packet

        # checksum added later in ExBus.py as it needs to include the packet id

        return exbus_packet, ex_packet

    def ex_frame(self, frametype=None,
                       data_1=None,
                       data_2=None,
                       text=None,
                       msg_class=None):
        '''Compile the EX telemetry packet (Header, data or text, etc.).'''

        if frametype == 'data':
            # put sensor data into ex frame
            data, length = self.Data(data_1=data_1, data_2=data_2)
        elif frametype == 'text':
            # put text data into ex frame
            data, length = self.Text(text=text)
        elif frametype == 'message':
            # put message data into ex frame
            data, length = self.Message(message=text, msg_class=msg_class)

        # compile header (types are 'text', 'data', 'message')
        header = self.Header(frametype, length)

        # compile the complete EX packet
        ex_packet = bytearray()
        ex_packet += header
        ex_packet += data

        # crc for telemetry (8-bit crc)
        # counting begins at the length byte of a message (skipping the header)
        crc8, crc8_int = CRC8.crc8(ex_packet[1:])

        # add crc8 to the packet ('B' is unsigned byte 8-bit)
        ex_packet += ustruct.pack('B', crc8_int)

        # compile simple text (34 bytes)
        # message = 'Greetings from chiefenne'
        # ex_packet += self.SimpleText(message)

        # self.logger.log('debug', 'ex_packet: {}'.format(ex_packet))
        # self.logger.log('debug', 'crc8: {}'.format(ustruct.pack('B', crc8_int)))

        return ex_packet, len(ex_packet)

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
        telemetry_length = length + const(6)

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

        # get variometer data if pressure sensor is present
        if self.current_sensor.category == 'PRESSURE':
            value_1, rel_altitude = self.variometer()
            value_2 = rel_altitude

        # compile 9th byte of EX data specification (2x 4bit)
        id1 = self.sensors.meta[data_1]['id'] << const(4)
        data_type = self.sensors.meta[data_1]['data_type']
        # combine bits for id and data type
        self.data += ustruct.pack('B', id1 | data_type)

        # data of 1st telemetry value, converted to EX format
        self.data += self.EncodeValue(value_1,
                                      self.sensors.meta[data_1]['data_type'],
                                      self.sensors.meta[data_1]['precision'])

        # compile 11th+x byte of EX data specification (2x 4bit)
        id2 = self.sensors.meta[data_2]['id'] << const(4)
        data_type = self.sensors.meta[data_2]['data_type']

        # combine bits for id and data type
        self.data += ustruct.pack('B', id2 | data_type)
        
        # data of 2nd telemetry value, converted to EX format
        self.data += self.EncodeValue(value_2,
                                      self.sensors.meta[data_2]['data_type'],
                                      self.sensors.meta[data_2]['precision'])

        return self.data, len(self.data)

    def Text(self, text=None):
        '''EX text packet. This transfers the sensor description and unit for
        one sensor value. Two text packets are needed to transfer the
        description and unit for one data packet (as it sends two values).
        '''

        extext = bytearray()
        # compile 9th byte of EX text specification (1 byte)
        id = self.sensors.meta[text]['id']
        extext += ustruct.pack('B', id)

        # compile 10th byte of EX text specification (5bits + 3bits)
        len_description = len(self.sensors.meta[text]['description'])
        len_unit = len(self.sensors.meta[text]['unit'])
        extext += ustruct.pack('B', len_description << 3 | len_unit)

        # compile 11th+x bytes of EX text specification
        description = self.sensors.meta[text]['description']
        for c in description:
            extext += bytes([ord(c)])

        # compile 11+x+y bytes of EX text specification (y bytes)
        unit = self.sensors.meta[text]['unit']
        for c in unit:
            extext += bytes([ord(c)])

        return extext, len(extext)

    def Message(self, message=None, msg_class=0):
        '''This message type allows transmitting any textual information directly
        to the pilot. Additional semantics can be added to the message
        (alarm/status/warning).'''

        message = bytearray()
        # compile 9th byte of EX message specification (1 byte)
        # identifyer of message type (0-255)
        message += ustruct.pack('B', 0)

        # compile 10th byte of EX message specification (3bits + 5bits)
        # message class (0-4)
        # 0: Basic informative message (really unimportant messages)
        # 1: Status message (device ready, motors armed, GPS position fix etc.)
        # 2: Warning (alarm, high vibrations, preflight conditions check, …)
        # 3: Recoverable error (loss of GPS position, erratic sensor data, …)
        # 4: Nonrecoverable error (peripheral failure, unexpected hardware fault, …)
        message += ustruct.pack('B', msg_class << 5 | len(message))

        # compile 11th+x bytes of EX message specification
        for c in message:
            message += bytes([ord(c)])

        return message, len(message)

    def Alarm(self, tone=False, code=None):
        '''EX packet alarm.'''
        alarm = bytearray()

        # number of bytes following (always 2)
        alarm += b'\x02'

        # 0x22 (without reminder tone, e.g. vario) or 0x23 (with reminder tone, e.g. low battery)
        alarm += b'\x23' if tone else b'\x22'

        # ASCII letter ('A' to 'Z') to be signalized by Morse alarm
        alarm += bytes([ord(code)])

        return alarm, len(alarm)

    def variometer(self):
        '''Calculate the variometer value derived from the pressure sensor.'''

        # calculate delta's for gradient
        # use ticks_diff to produce correct result (when timer overflows)
        self.vario_time = time.ticks_ms()
        dt = time.ticks_diff(self.vario_time, self.vario_time_old) / 1000.0
        dz = self.current_sensor.relative_altitude - self.last_altitude

        # calculate the climbrate
        climbrate = dz / (dt + 1.e-9)

        # deadzone filtering
        if climbrate > self.deadzone:
            climbrate -= self.deadzone
        elif climbrate < -self.deadzone:
            climbrate += self.deadzone
        else:
            climbrate = 0.0

        # smoothing filter for the climb rate
        climbrate = climbrate + self.vario_smoothing * \
            (self.last_climbrate - climbrate)

        # store data for next iteration
        self.vario_time_old = self.vario_time
        self.last_altitude = self.current_sensor.relative_altitude
        self.last_climbrate = climbrate

        return climbrate, self.current_sensor.relative_altitude

    def SimpleText(self, text):
        '''EX packet simple text (must be 34 bytes long).
        This text is shown on the Jetibox.

        32 bytes of text are needed + 2 bytes for the separators.
        The simple text is concatenated to every telemetry packet.
        8th bit of message separators needs to be 0
        8th bit of each text character needs to be 1
        '''

        # crop text if too long, fill up if needed, left adjusted
        # 32 bytes are reserved for the text
        text = '{:<32}'.format(text[:32])

        simple_text = bytearray()

        # separator of message (begin), clear 8th bit
        simple_text += (0xFE & ~(1 << 7)).to_bytes(1, 'little')

        # add the text to the packet, set 8th bit
        for c in text:
            simple_text += bytes([ord(c) | (1 << 7)])

        # separator of message (end), clear 8th bit
        simple_text += (0xFF & ~(1 << 7)).to_bytes(1, 'little')

        return simple_text

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

        # FIXME: only innt14_t hardcoded for the moment
        # FIXME: only innt14_t hardcoded for the moment
        # FIXME: only innt14_t hardcoded for the moment

        # format for pack
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
