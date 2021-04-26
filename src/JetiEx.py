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
     The simple text is concatenated to every telemetry package

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

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from ubinascii import hexlify, unhexlify

import Logger

# setup a logger for the REPL
logger = Logger.Logger()


class JetiEx:
    '''Jeti EX protocol implementation. 
    '''

    def __init__(self):
        self.header = bytearray()
        self.data = bytearray()
        self.text = bytearray()
        self.message = bytearray()
        self.alarm = bytearray()
        self.simple_text = bytearray()
        self.packet = bytearray()

        self.i2c_sensors = None

        # setup a logger for the REPL
        self.logger = Logger.Logger()

    def Header(self):
        pass

    def Data(self):
        pass

    def Text(self):
        pass

    def Message(self):
        pass

    def Alarm(self):
        '''[summary]
        '''

    def SimpleText(self, text):
        '''Messages to be displayed on the JetiBox.
        The packet is always 34 bytes long, inlcuding 2 message separator bytes (begin, end).
        So each message has to have 32 bytes of text.

        Args:
            text (str): A simple text message (maximum 32 characters)

        '''

        # do a hard limit on the text length (limit to max allowed)
        if len(text) > 32:
            self.logger.log('debug', 'Text too long for simple text.')
            text = text[:32]

        # separator of message (begin)
        begin = bytearray.fromhex('FE')
        self.simple_text.extend(begin)

        # add the text to the packet
        text_encoded = text.encode('utf-8')
        text_hex = hexlify(text_encoded)
        self.simple_text.extend(text_hex)

        # separator of message (end)
        end = bytearray.fromhex('FF')
        self.simple_text.extend(end)

        return self.simple_text

    def Sensors(self, i2c_sensors):
        self.i2c_sensors = i2c_sensors

    def Packet(self, sensor):

        packet = b''

        return packet

