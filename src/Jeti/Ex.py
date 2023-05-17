'''Python Implementation of the JETI EX protocol

This protocol describes how data, text, messages and alarms are sent to
and from the Jeti receiver.

The EX protocol is used in two ways:
  - In older Jeti devices at lower communication speed (9600-9800 baud)
  - As part of the newer "EX Bus" protocol (125 or 250kbaud)

In both cases it carries the telemetry data (data, text, message, alarms).

This is used from within the Jeti EX Bus protocol. So the Jeti EX Bus protocol
carries data with this Jeti EX protocol. 


1) EX Packet

  a) Message Header

    Byte |  Length |     Data     |  Description
   ------|---------|--------------|----------------------------------------
     1   |    1B   |     0x7E     |  Separator of the message
     2   |    1B   |     0xNF     |  Distinct identifier of an EX packet (n is an arbitrary number)
     3   |    2b   |  Type (0-3)  |  0 - Text, 1 – Data, 2 – Message
     3   |    6b   | Length (0-31)|  Length of a packet (number of bytes following)
    4-5  |    2B   |       SN     |  Upper part of a sensors serial number, Manufacturer ID (Little Endian)
    6-7  |    2B   |       SN     |  Lower part of a sensors serial number, Device ID (Little Endian)
     8   |    1B   |     0x00     |  Reserved

   NOTE: Byte 3 of the packet is split into 2 and 6 bits (B=Byte, b=bit)
   NOTE: The upper part of the serial number should be in the range 0xA400 – 0xA41F
         The lower part of a serial number should be used in a manner it
         ensures uniqueness of the whole serial number
   NOTE: Maximum allowed length of a packet is 29B (together with separators 0x7E; 0xNF)

   Bytes 3 to 8 make up the message header. Depending on byte 3 [2bits] which
   is the packet type, there follow three different specifications (data, text, message)
   for the rest of the bytes of the packet.

  b1) Data specification

    Byte  |  Length |    8 data bits    |  Description
   -------|---------|-------------------|----------------------------------------
     9    |    4b   | Identifier (0-15) |  Identifier of telemetry value
     9    |    4b   |  Data type (0-15) |  Data type of telemetry value
    10    |    xB   |        Data       |  Data with length according to data type
    11+x  |    4b   | Identifier (1-15) |  Identifier of a second telemetry value
    11+x  |    4b   |  Data type (0-15) |  Data type of a second telemetry value
    12+x  |    yB   |        Data       |  Data with length according to data type
    13+x+y|    1B   |        CRC8       |  Cyclic redundancy check

  b2) Text specification

    Byte  |  Length |            8 data bits          |  Description
   -------|---------|---------------------------------|----------------------------------------
     9    |    1B   |       Identifier (0-255)        |  Identifier of telemetry value
    10    |    5b   | Length of the description (x)   |  Length of the description in Bytes
    10    |    3b   | Length of unit's description (y)|  Length of the unit's description in Bytes
    11    |    xB   |                Label            |  ASCII textual description of a value
    11+x  |    yB   |                Label            |  ASCII textual description of a unit
    11+x+y|    1B   |                 CRC8            |  Cyclic redundancy check

  b3) Message specification

    Byte   |  Length |       8 data bits         |  Description
   --------|---------|---------------------------|----------------------------------------
     9     |    1B   |    Message type (0-255)   |  Primary identifier of the message type. Value is used for additional semantic information and localization.
    10[7:5]|    3b   |    Message class          |  Class identifier of the message type. Gives additional semantics
    10[4:0]|    5b   | Length of the message (x) |  Length of the message in bytes
    11     |    xB   |          Message          |  UTF-8 message
    11+x   |    1B   |             CRC8          |  Cyclic redundancy check

  Message class semantics:
    Message class  |   Description
   ----------------|----------------------------------------------------
           0       | Basic informative message (really unimportant messages)
           1       | Status message (device ready, motors armed, GPS position fix etc.)
           2       | Warning (alarm, high vibrations, preflight conditions check, …)
           3       | Recoverable error (loss of GPS position, erratic sensor data, …)
           4       | Nonrecoverable error (peripheral failure, unexpected hardware fault, …)
           5       | Reserved
           6       | Reserved
           7       | Reserved

  c) Simple text protocol
     The simple text is concatenated to every telemetry packet

    Byte  |  Length |8 data bits|  Bit 8 |   Description
   -------|---------|------------|-------|-----------------------------
     1    |    1B   |    0xFE    |    0  | Separator of a message (begin)
     2    |    1B   | 'T' (0x54) |    1  | ASCII character
     3    |    1B   | 'E' (0x45) |    1  | ASCII character
     4    |    1B   | 'X' (0x58) |    1  | ASCII character
     5    |    1B   | 'T' (0x54) |    1  | ASCII character
   ...    |   ...   |     ...    |    0  | ...
   ...    |   ...   |     ...    |    0  | ...
   ...    |   ...   |     ...    |    0  | ...
    34    |    1B   |    0xFF    |    0  | Separator of a message (end)


  d) Protocol of alarms
     Protocol includes a letter encoded in Morse Code alphabet, which is later acoustically signalized

    Byte  | 8 data bits| Bit 8 |   Description
   -------|------------|-------|-------------------------------
     1    |    0x7E    |    0  | Separator of a message
     2    |    0xNL    |    1  | L = number of bytes following (always 2), N can be any number
     3    |  0x22/0x23 |    1  | 0x22- without reminder tone (Vario); 0x23 – with reminder tone (standard alarm)
     4    |   'A'-'Z'  |    1  | ASCII letter to be signalized by Morse alarm


NOTE on EX data types:
There exist 16 data types. The most used are int14_t, int22_t and int30_t.                 
The upper 3 bits of the telemetry value are reserved for sign (1 bit) and the
position of the decimal point (2 bits).

Example for int14_t (needs 2 bytes = 16 bits). 3 bits are needed for sign and
decimal position, so 13 bits are left for the value (2^13 = 8192). This means
together with the sign and zero the data range is from -8191 to 8191.

    Telemetry:
        value = 115.3
    Convert scaled value to hex:
        hex(1153) --> '0x481'
    Convert sign (0 for +, 1 for -) and decimal point position (01):
        hex(001) --> '0x1'
    Combine results:
        '0x1481'

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from ubinascii import hexlify, unhexlify
import ujson
import utime
import ustruct

from Jeti import CRC8
from Utils.Logger import Logger
import Utils.lock as lock


class Ex:
    '''Jeti EX protocol handler. 
    '''

    def __init__(self, sensors):

        # list of sensors
        self.sensors = sensors

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

    def frame(self, sensor):
        '''Compile the telemetry packet (Header, data or text, etc.)

        Returns:
            packet (hex): The complete packet describing the telemetry
        '''
        self.current_sensor = sensor

        # acquire lock
        self.lock()

        self.packet = bytearray()

        data = self.Data()

        # packet length only known after data, text
        # packet types text=0, data=1, message=2
        type = 1
        header = self.Header(type, len(data))

        # compile simple text protocol
        message = 'Hallodrio'
        text = self.SimpleText(message)

        # compose packet
        self.packet += header

        # add data
        self.packet += data

        # crc for telemetry (8-bit crc)
        crc8 = CRC8.crc8(self.packet[2:])
        self.packet += crc8

        self.packet += text

        # release lock
        self.release()

        return self.packet

    def Header(self, ptype, length):
        '''EX packet header'''

        header = bytearray()

        # combine productID and deviceID (2 bytes), LSB first, MSB last
        productID = self.sensors.productID
        deviceID = ustruct.pack('b', self.current_sensor.deviceID) + b'\x00'

        # message separator (1st byte)
        header += b'\x7E'

        # packet identifier '0xnF', with 'n' beeing any number (2nd byte)
        header += b'\x0F'

        # 2 bits for packet type (0=text, 1=data, 2=message)
        # these are the two leftmost bits of 3rd byte; shift left by 6
        telemetry_type = ptype << 6

        # 6 bits (right part of 3rd byte) for packet length (max. 29 bytes)
        # telemetry_length is the number of bytes of data/text packet
        telemetry_length = 5 + length + 10

        # combine 2+6 bits (3rd byte)
        type_length = telemetry_type | telemetry_length
        header += ustruct.pack('b', type_length)

        # serial number (bytes 4-5 and 6-7)
        header += productID
        header += deviceID

        # reserved (8th byte)
        header += b'\x00'

        return header

    def Data(self):

        data = bytearray()


        if self.current_sensor.type == 'pressure':

            # compile 9th byte of EX data specification (2x 4bit)
            # 1st 4bit (from left): sensor id, 2nd 4bit: data type
            id = self.sensors.ID_PRESSURE << 4
            type = self.sensors.meta['ID_PRESSURE']['data_type']
            id_type = id | type
            # convert int to bytes (e.g. 20 --> b'\x14') and append to data
            data += ustruct.pack('b', id_type)

            # data of 1st telemetry value
            nbytes = self.sensors.meta['ID_PRESSURE']['bytes']
            precision = self.sensors.meta['ID_PRESSURE']['precision']
            value = self.current_sensor.pressure
            sign = 0 if value >= 0x0 else 1
            value_s = int(value * 10**precision)

            # convert value to EX format
            val = sign << (nbytes*8 - 1) | precision << (nbytes*8 - 3) | value_s

            data += ustruct.pack('b', val)

            # compile 11th+x byte of EX data specification (2x 4bit)
            id = self.sensors.ID_TEMP << 4
            type = self.sensors.meta['ID_TEMP']['data_type']
            id_type = id | type
                                         
            # data of 2nd telemetry value
            nbytes = self.sensors.meta['ID_TEMP']['bytes']
            precision = self.sensors.meta['ID_TEMP']['bytes']
            value = self.current_sensor.temperature
            sign = 0 if value >= 0x0 else 1
            value_s = int(value * 10**precision)

            # convert value to EX format
            val = sign << (nbytes*8 - 1) | precision << (nbytes*8 - 3) | value_s

        return data

    def Text(self, sensor):

        if sensor['type'] == 'pressure':

            # get value to be sent
            value = 'pressure' if sensor[val[0]]['toggle'] else 'temperature'

            # print toggle value for debugging
            # print('value', value)

            self.text = list()
            # compile 9th byte of EX text specification (1 byte)
            id_press = sensor[value]['id']
            self.text.append('{:02x}'.format(id_press))

            # compile 10th byte of EX text specification (5bits + 3bits)
            len_description = len(sensor[value]['description']) << 3
            len_unit = len(sensor[value]['unit'])

            len_description_unit = len_description | len_unit
            self.text.append('{:02x}'.format(len_description_unit))

            description = sensor[value]['description']
            self.text.append(hexlify(description))

            unit = sensor[value]['unit']
            self.text.append(hexlify(unit))

    def SimpleText(self, text):
        '''Messages to be displayed on the JetiBox.
        The packet is always 34 bytes long, inlcuding 2 message separator bytes (begin, end).
        
        All separators have bit No. 8 set to log. zero. Other characters (simple text) have
        this bit set to log. 1. It is mandatory to transmit the whole packet consisting
        of 34 bytes and it is not possible to send only a part of text.

        Args:
            text (str): A simple text message (maximum 32 characters)
        '''

        self.simple_text = bytearray()

        # crop text if too long and fill up if needed (no rjust() in MicroPython)
        text = '{:>32}'.format(text[:32])

        # separator of message (begin)
        self.simple_text += b'\xFE'

        # add the text to the packet
        self.simple_text += hexlify(text)

        # separator of message (end)
        self.simple_text += b'FF'

        return self.simple_text

    def value_to_EX(self, value=None, nbytes=2, precision=1, endian='little'):
        '''Convert a value to the EX protocol specification

        Args:
            value (int, float): Any telemetry value
            nbytes (int): Number of bytes (uint6_t = 1, uint14_t = 2, etc.)
            precision ([type]): [description]

        Returns:
            (hex): Hex string describing the value
        '''

        # get the sign of the value
        sign = 0 if value >= 0x0 else 1

        # use value without sign (as this is transferred on MSB)
        value = abs(value)

        # scale value according to precision
        scaled_value = int(value * 10**precision) if precision > 0 else int(value)

        # compile hex string from above
        val = sign << (nbytes*8 - 1) | precision << (nbytes*8 - 3) | scaled_value
        hex_str = hex(val)[2:]

        # compile even number of hex (add leading "0")
        if len(hex_str) % 2 == 1:
            hex_str = '0' + hex_str

        # split hex into list of pairs
        hex_str = [hex_str[i:i+2] for i in range(0,len(hex_str), 2)]
	
	    #  reverse bytes if little endian is required
        if endian == 'little':
            hex_str.reverse()

        return [e.encode('utf-8') for e in hex_str]

    def bytes2hex(self, _bytes, separator='-'):
        p_d = _bytes.decode()
        hex_str = separator.join([p_d[x:x+2] for x in range(0, len(p_d), 2)])
        return hex_str
