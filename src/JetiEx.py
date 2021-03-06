'''Python Implementation of the JETI EX protocol

This protocol describes how data, text, messages and alarms are sent to
and from the Jeti receiver.

The EX protocol is used in two ways:
  - In older Jeti devices at lower communication speed (9600-9800 baud)
  - As part of the newer "EX Bus" protocol (125 or 250kbaud).

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
    4-5  |    2B   |       SN     |  Upper part of a serial number, Manufacturer ID (Little Endian)
    6-7  |    2B   |       SN     |  Lower part of a serial number, Device ID (Little Endian)
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
together with the sign and zero the data range is fomr -8191 to 8191.

    Telemetry:
        value = 115.3
    Convert scaled value to hex:
        hex(1153) --> '0x481'
    Convert sign (0 = +) and decimal point position (01):
        hex(001) --> '0x1'
    Combine results:
        '0x1481'

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from ubinascii import hexlify, unhexlify
import ujson
import utime

import CRC8
import Logger

# setup a logger for the REPL
logger = Logger.Logger()


class JetiEx:
    '''Jeti EX protocol implementation. 
    '''

    def __init__(self):

        self.getSerialNumber()


        self.i2c_sensors = None
        self.toggle_value = False

        # setup a logger for the REPL
        self.logger = Logger.Logger()

    def getSerialNumber(self, filename='serial_number.json'):

        with open(filename, 'r') as fp:
	        serial_number = ujson.load(fp)

        # upper part of the serial number (range 0xA400 – 0xA41F)
        self.productID = serial_number['productID']['lower'] + \
                         serial_number['productID']['upper']

        # lower part of the serial number
        self.deviceID = serial_number['deviceID']['lower'] + \
                        serial_number['deviceID']['upper']

        return serial_number

    def Header(self, packet_type):
        '''EX packet header'''

        self.header = bytearray()

        packet_types = {'text': 0, 'data': 1, 'message': 2}

        # message separator (1st byte)
        self.header.extend(b'7E')

        # packet identifier '0xnF', with 'n' beeing any number (2nd byte)
        self.header.extend(b'3F')

        # 2 bits for packet type (0=text, 1=data, 2=message)
        # these are the two leftmost bits of 3rd byte; shift left by 6
        telemetry_type = packet_types[packet_type] << 6

        # 6 bits (right part of 3rd byte) for packet length (max. 29 bytes)
        # telemetry_length is the number of bytes of data/text packet
        telemetry_length = 5 + self.telemetry_length + 10

        # combine 2+6 bits (3rd byte)
        type_length = telemetry_type | telemetry_length
        self.header.extend(hex(type_length)[2:])

        # serial number (bytes 4-5 and 6-7)
        self.header.extend(self.productID)
        self.header.extend(self.deviceID)

        # reserved (8th byte)
        self.header.extend(b'00')

    def Data(self, sensor):

        # get dictionary with sensor specs
        sensor_specs = self.i2c_sensors.available_sensors[sensor]

        # read method has to be available in each sensor driver
        values = self.i2c_sensors.read(sensor)

        if sensor_specs['type'] == 'pressure':
            pressure = values[0]
            temperature = values[1]

            # compile 9th byte of EX data specification (2x 4bit)
            id_press = sensor_specs['EX']['pressure']['id'] << 4
            data_type_press = sensor_specs['EX']['pressure']['data_type']
            id_data_type_press = id_press | data_type_press

            # data of 1st telemetry value
            bytes_press = sensor_specs['EX']['pressure']['bytes']
            prec_press = sensor_specs['EX']['pressure']['precision']
            self.data1 = self.value_to_EX(value=pressure, nbytes=bytes_press,
                                         precision=prec_press, endian='little')

            # compile 11th+x byte of EX data specification (2x 4bit)
            id_temp = sensor_specs['EX']['temperature']['id'] << 4
            data_type_temp = sensor_specs['EX']['temperature']['data_type']
            id_data_type_temp = id_temp | data_type_temp
                                         
            # data of 2nd telemetry value
            bytes_temp = sensor_specs['EX']['temperature']['bytes']
            prec_temp = sensor_specs['EX']['temperature']['precision']
            self.data2 = self.value_to_EX(value=temperature, nbytes=bytes_temp,
                                         precision=prec_temp, endian='little')

            self.telemetry_length = len(self.data1) + len(self.data2)

            self.data = list()
            self.data.append('{:02x}'.format(id_data_type_press))
            self.data.extend(self.data1)

            self.data.append('{:02x}'.format(id_data_type_temp))
            self.data.extend(self.data2)

        return self.data

    def Text(self, sensor):

        # get dictionary with sensor specs
        sensor_specs = self.i2c_sensors.available_sensors[sensor]

        if sensor_specs['type'] == 'pressure':

            # toggle text for the two telemetry values
            self.toggle_value ^= True
            val = {1: 'pressure', 0: 'temperature'}
            value = val[self.toggle_value]

            # print toggle value for debugging
            # print('value', value)

            self.text = list()
            # compile 9th byte of EX text specification (1 byte)
            id_press = sensor_specs['EX'][value]['id']
            self.text.append('{:02x}'.format(id_press))

            # compile 10th byte of EX text specification (5bits + 3bits)
            len_description = len(sensor_specs['EX'][value]['description']) << 3
            len_unit = len(sensor_specs['EX'][value]['unit'])

            len_description_unit = len_description | len_unit
            self.text.append('{:02x}'.format(len_description_unit))

            description = sensor_specs['EX'][value]['description']
            self.text.append(hexlify(description))

            unit = sensor_specs['EX'][value]['unit']
            self.text.append(hexlify(unit))

    def Message(self):
        pass

    def Alarm(self, sensor):
        '''[summary]
        '''

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
        self.simple_text.extend(b'FE')

        # add the text to the packet
        self.simple_text.extend(hexlify(text))

        # separator of message (end)
        self.simple_text.extend(b'FF')

        return self.simple_text

    def Sensors(self, i2c_sensors):
        self.i2c_sensors = i2c_sensors

    def ExPacket(self, sensor, packet_type):
        '''Compile the telemetry packet (Header, data or text, etc.)

        Args:
            sensor (str): Sensor ID (e.g. 'BME280')
            packet_type (str): Any of 'data', 'text', 'message'

        Returns:
            packet (hex): The complete packet describing the telemetry
        '''

        packet = bytearray()

        if packet_type == 'data':
            self.Data(sensor)
        elif packet_type == 'text':
            self.Text(sensor)

        # packet length only known after data, text
        self.Header(packet_type)

        # compile simple text protocol
        text = 'Hallodrio'
        self.SimpleText(text)
        # print('self.simple_text (JetiEx.py)', self.bytes2hex(self.simple_text))

        # compose packet
        packet.extend(self.header)

        if packet_type == 'data':
            for element in self.data:
                packet.extend(element)
        elif packet_type == 'text':
            for element in self.text:
                packet.extend(element)

        # crc for telemetry (8-bit crc)
        crc = CRC8.crc8(packet[2:])
        self.header.extend(crc)

        packet.extend(self.simple_text)

        # print in readable format
        # print('Ex Packet (JetiEx.py)', self.bytes2hex(packet))

        return packet

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
