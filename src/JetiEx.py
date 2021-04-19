'''Python Implementation of the JETI Ex protocol

This protocol describes how data, text and messages are sent to and from the
Jeti receiver.

This is used from within the Jeti Ex Bus protocol.


1) Packet 

    Byte | Length |     Data     |  Description
   ------|--------|--------------|----------------------------------------
     1   |    1   |     0x7E     |  Header
     2   |    1   |     0x01     |  Header
     3   |    1   |      LEN     |  Message length incl. CRC
     4   |    1   |       ID     |  Packet ID
     5   |    1   |     0x3A     |  Identifier for a telemetry request
     6   |    1   |        0     |  Length of data block
    7/8  |    2   |    CRC16     |  CRC16-CCITT in sequence LSB, MSB             |

1 1B 0x7E 0 Separator of the message

Little endian and big endian can be modified via the struct module:
struct.pack('>i', 0x31323334) --> b'1234'
struct.pack('<i', 0x31323334) --> b'4321'

'''


class JetiEx:

    def __init__(self):
        pass

