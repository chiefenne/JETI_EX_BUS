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
import micropython
from micropython import const

from Jeti import CRC8
from Utils.Logger import Logger
from Utils.round_robin import cycler
from Utils import status
from Utils.alpha_beta_filter import AlphaBetaFilter


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
        self.max_altitude = 0
        self.max_climb = 0
        self.vario_time_old = time.ticks_ms()

        # exponential filter
        self.vario_smoothing = 0.81

        # alpha-beta filter
        alpha = 0.02
        beta = 0.005
        self.vario_filter = AlphaBetaFilter(alpha=alpha,
                                            beta=beta,
                                            initial_value=0,
                                            initial_velocity=0,
                                            delta_t=1)

        # initialize the EX BUS packet 
        # needed for check in ExBus.py, set to 'True' in main.py
        self.exbus_data_ready = False
        self.exbus_device_ready = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EX')

    @micropython.native
    def run_forever(self):
        '''Run the EX protocol forever.
        The EX BUS protocol is also prepared here.
        '''

        # get all attached sensors (access object only once = speed up)
        active_sensors = self.sensors.get_sensors()

        # make a generator out of the list of sensors
        cycle_sensors = cycler(active_sensors)

        # device name and description/units of all available sensors
        # this can be send once (or a few times) at the beginning of the telemetry
        # the transmitter stores the information and associates later the labels
        # with the telemetry data by their id
        # see also in ExBus.py (sendTelemetry method)
        labels = list()
        for sensor in active_sensors:
            labels += sensor.labels
        # insert 'DEVICE' as first label
        labels.insert(0, 'DEVICE')

        self.lock.acquire()
        self.dev_labels_units = list()
        for label in labels:
            # frames for device, labels and units
            self.dev_labels_units.append(self.exbus_frame(frametype=0, label=label))
        self.n_labels = len(labels)
        self.exbus_device_ready = True
        self.lock.release()

        # acquire sensor data and prepare EX BUS telemetry
        while True:

            # cycle infinitely through all sensors
            current_sensor = next(cycle_sensors)
            category = current_sensor.category # cache variable

            # collect data from currently selected sensor
            current_sensor.read_jeti()

            # update data frame (new sensor data)
            if category == 'PRESSURE':
                pressure = current_sensor.pressure / 100.0 # convert to hPa (mbar)
                temperature = current_sensor.temperature
                relative_altitude = current_sensor.relative_altitude
                # variometer
                climb, altitude = self.variometer(relative_altitude,
                                                  filter='alpha_beta')
                self.max_altitude = max(self.max_altitude, altitude)
                self.max_climb = max(self.max_climb, climb)
                
                data = {'PRESSURE': pressure,              # 3 bytes
                        'TEMPERATURE': temperature,        # 2 bytes
                        'CLIMB': climb,                    # 2 bytes
                        'MAX_CLIMB': self.max_climb,       # 2 bytes
                        'ALTITUDE': altitude,              # 2 bytes
                        'MAX_ALTITUDE': self.max_altitude} # 2 bytes
            elif category == 'VOLTAGE':
                pass
            elif category == 'CURRENT':
                pass
            elif category == 'CAPACITY':
                pass
            elif category == 'RPM':
                rpm = current_sensor.rpm
                data = {'RPM': rpm}
            elif category == 'GPS':
                data = {'GPSLAT',
                                self.GPStoEX(current_sensor.longitude, longitude=True),
                                'GPSLON', 
                                self.GPStoEX(current_sensor.latitude, longitude=False)}

            self.lock.acquire()
            self.exbus_data = self.exbus_frame(frametype=const(1), data=data) # data
            self.exbus_data_ready = True
            self.lock.release()

    @micropython.native
    def exbus_frame(self, frametype=None, label=None, data=None):
        '''Prepare the EX BUS telemetry packet.
        It includes the EX packet and the EX BUS header.
         is added later in ExBus.py as it needs to include the packet id.
        '''

        # setup ex packet
        ex_packet, len_ex = self.ex_frame(frametype=frametype,
                                          data=data,
                                          label=label)

        # initiliaze the EX BUS packet
        exbus_packet = bytearray()

        # EX bus header
        exbus_packet += b'\x3B\x01'

        # EX bus packet length in bytes including the header and CRC
        exbus_packet += ustruct.pack('B', len_ex + const(8))
        
        # put dummy id here; will be replaced by packet id later
        exbus_packet += b'\x00'

        # telemetry identifier
        exbus_packet += b'\x3A'

        # EX packet length (including 0xF and crc8 bytes)
        exbus_packet += ustruct.pack('B', len_ex)

        # add EX packet
        exbus_packet += ex_packet

        # checksum added later in ExBus.py as it needs to include the packet id

        # return as bytes, to stay immutable!!!
        # bytearray caused troubles in ExBus.sendTelemetry
        return bytes(exbus_packet)

    @micropython.native
    def ex_frame(self, frametype=None, data=None, label=None):
        '''Compile the EX telemetry packet (Header, data or text, etc.).'''

        if frametype == const(1): # data
            # put sensor data into ex frame
            data, length = self.Data(data=data)
        elif frametype == const(0): # text
            # put text data into ex frame
            data, length = self.Text(label=label)
        elif frametype == const(2): # message
            # put message data into ex frame
            message = 'Greetings from chiefenne'
            data, length = self.Message(message=message, msg_class=const(0))

        # compile header (types are 'text', 'data', 'message')
        header = self.Header(frametype, length)

        # compile the complete EX packet
        ex_packet = bytearray()
        ex_packet += header
        ex_packet += data

        # crc for telemetry (8-bit crc)
        # counting begins at the length byte of a message (skipping the header)
        crc8_int = CRC8.crc8_viper(ex_packet[1:], len(ex_packet[1:]))

        # add crc8 to the packet ('B' is unsigned byte 8-bit)
        ex_packet += ustruct.pack('B', crc8_int)

        # compile simple text for JETI box (34 bytes)
        # message = 'Greetings from chiefenne'
        # ex_packet += self.SimpleText(message)

        return ex_packet, len(ex_packet)

    @micropython.native
    def Header(self, frametype, length):
        '''EX packet message header.'''

        header = bytearray()

        # message separator - not needed if EX frame is embedded in EX BUS frame
        # header += b'\x7E'

        # packet identifier
        header += b'\x0F'

        # 2 bits for packet type (0=text, 1=data, 2=message)
        # these are the two leftmost bits of 3rd byte; shift left by 6
        telemetry_type = frametype << const(6)

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

    @micropython.native
    def Data(self, data=None):
        '''EX data packet. Maximum length including the header and crc8 is 29 bytes.'''

        exdata = bytearray()

        # speed up obejct access
        meta = self.sensors.meta

        for telemetry, value in data.items():
            meta_tele = meta[telemetry] # speed up object access
            # compile 9th byte onwards of EX data specification
            id = meta_tele['id'] << const(4)
            data_type = meta_tele['data_type']
            # combine bits for id and data type
            exdata += ustruct.pack('B', id | data_type)

            # data of 1st telemetry value, converted to EX format
            # scale value based on precision and round it
            mult = -1 if value < 0 else 1
            value_scaled = int(value * 10**meta_tele['precision'] + mult * 0.5)
            exdata += self.EncodeValue(value_scaled,
                                     meta_tele['data_type'],
                                     meta_tele['precision'])

        return exdata, len(exdata)

    @micropython.native
    def Text(self, label=None):
        '''EX text packet. This transfers the sensor description and unit for
        one sensor value.
        Maximum length including the header and crc8 is 29 bytes.
        '''

        # cache object
        meta_label = self.sensors.meta[label]
        id = meta_label['id']
        description = meta_label['description']
        unit = meta_label['unit']

        # initiliaze the EX BUS packet
        extext = bytearray()

        # compile 9th byte of EX text specification (1 byte)
        extext += ustruct.pack('B', id)

        # compile 10th byte of EX text specification (5bits + 3bits)
        extext += ustruct.pack('B', len(description) << 3 | len(unit))

        # compile 11th+x bytes of EX text specification
        extext += bytes([ord(c) for c in description])

        # compile 11+x+y bytes of EX text specification (y bytes)
        extext += bytes([ord(c) for c in unit])

        return extext, len(extext)

    @micropython.native
    def Message(self, message=None, msg_class=const(0)):
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
        message += ustruct.pack('B', msg_class << const(5) | len(message))

        # compile 11th+x bytes of EX message specification
        message += bytes([ord(c) for c in message])

        return message, len(message)

    @micropython.native
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

    @micropython.native
    def variometer(self, altitude, filter='alpha_beta'):
        '''Calculate the variometer value derived from the pressure sensor.'''

        # calculate delta's for gradient
        # use ticks_diff to produce correct result (when timer overflows)
        vario_time = time.ticks_ms()
        dt = time.ticks_diff(vario_time, self.vario_time_old) / 1000.0
        dz = altitude - self.last_altitude

        # calculate the climbrate
        climbrate_raw = dz / (dt + 1.e-9)

        if filter == 'exponential':
            # smoothing filter for the climb rate
            climbrate = climbrate_raw + \
                self.vario_smoothing * (self.last_climbrate - climbrate_raw)
        elif filter == 'alpha_beta':
            # alpha-beta filter for the climb rate
            climbrate = self.vario_filter.update(climbrate_raw)
        else:
            climbrate = climbrate_raw

        # store data for next iteration
        self.vario_time_old = vario_time
        self.last_altitude = altitude
        self.last_climbrate = climbrate

        return climbrate, self.last_altitude

    @micropython.native
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

    @micropython.viper
    def EncodeValue(self, value_scaled: int, dataType: int, precision: int):
        '''Encode telemetry value.

        Returns:
            value_ex : encoded value as bytes in little endian format
        
            
        Data type | Description |  Note
        ----------|-------------|---------------------------------------
            0     |   int6_t    |  Data type  6b (-31 ,31)
            1     |   int14_t   |  Data type 14b (-8191 ,8191)
            4     |   int22_t   |  Data type 22b (-2097151 ,2097151)
            5     |   int22_t   |  Data type 22b (-2097151 ,2097151), time and date
            8     |   int30_t   |  Data type 30b (-536870911 ,536870911)
            9     |   int30_t   |  Data type 30b (-536870911 ,536870911), GPS

        '''

        # zero must be positive, otherwise wrong value is encoded
        sign = 0x01 if value_scaled < 0 else 0x00

        # combine sign, precision and scaled value
        if dataType == 0: # int6_t
            lo_byte = (value_scaled & 0x1F) | sign << 7 | (precision << 5)
            value_ex = ustruct.pack('b', lo_byte)
        elif dataType == 1: # int14_t
            lo_byte = value_scaled & 0xFF
            hi_byte = ((value_scaled >> 8) & 0x1F) | (sign << 7) | (precision << 5)
            value_ex = ustruct.pack('bb', lo_byte, hi_byte)
        elif dataType == 4: # int22_t
            lo_byte = value_scaled & 0xFF
            mid_byte = ((value_scaled >> 8) & 0xFF)
            hi_byte = ((value_scaled >> 16) & 0x1F) | (sign << 7) | (precision << 5)
            value_ex = ustruct.pack('bbb', lo_byte, mid_byte, hi_byte)
        elif dataType == 5: # int22_t, time and date
            lo_byte = value_scaled & 0xFF
            mid_byte = ((value_scaled >> 8) & 0xFF)
            hi_byte = ((value_scaled >> 16) & 0xFF) | (sign << 7)
            value_ex = ustruct.pack('bbb', lo_byte, mid_byte, hi_byte)
        elif dataType == 8: # int30_t
            lo_byte = value_scaled & 0xFF
            mid_byte = ((value_scaled >> 8) & 0xFF)
            hi_byte = ((value_scaled >> 16) & 0xFF)
            ex_byte = ((value_scaled >> 24) & 0x1F) | (sign << 7) | (precision << 5)
            value_ex = ustruct.pack('bbbb', lo_byte, mid_byte, hi_byte, ex_byte)
        elif dataType == 9: # int30_t, GPS
            lo_byte = value_scaled & 0xFF
            mid_byte = ((value_scaled >> 8) & 0xFF)
            hi_byte = ((value_scaled >> 16) & 0xFF)
            ex_byte = ((value_scaled >> 24) & 0xFF)
            value_ex = ustruct.pack('bbbb', lo_byte, mid_byte, hi_byte, ex_byte)

        return value_ex

    @micropython.native
    def GPStoEX(self, value, longitude=True):
        '''Convert GPS coordinates to EX format.
        The GPS coordinates are given in decimal format.
        '''
        # Decompose the value into degrees and minutes
        deg, frac = divmod(abs(value), 1)
        deg16 = int(deg)
        min16 = int(abs(frac) * 0.6 * 100000)

        # Compute the four bytes
        lo_byte = min16 & 0xFF
        mid_byte = (min16 >> 8) & 0xFF
        hi_byte = deg16 & 0xFF
        ex_byte = ((deg16 >> 8) & 0x01) | (longitude << 5) | ((value < 0) << 6)

        value_ex = ustruct.pack('bbbb', lo_byte, mid_byte, hi_byte, ex_byte)

        return value_ex

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
        self.logger.log(
            'debug', 'core 1: EX, lock released after {} us'.format(diff))
