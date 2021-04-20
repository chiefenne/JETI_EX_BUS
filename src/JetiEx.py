'''Python Implementation of the JETI Ex protocol

This protocol describes how data, text and messages are sent to and from the
Jeti receiver.

This is used from within the Jeti Ex Bus protocol.


1) EX Packet

    Byte |  Length |     Data     |  Description
   ------|---------|--------------|----------------------------------------
     1   |    1B   |     0x7E     |  Separator of the message
     2   |    1B   |     0xNF     |  Distinct identifier of an EX packet (n is an arbitrary number)
     3   |    2b   |  Type (0-3)  |  0 - Text, 1 – Data, 2 – Message
     3   |    6b   | Length (0-31)|  Length of a packet (number of bytes following)
    4-5  |    2B   |       SN     |  Upper part of a serial number, Manufacturer ID (Little Endian)
    6-7  |    2B   |       SN     |  Lower part of a serial number, Device ID (Little Endian)
     8   |    1B   |     0x00     |  Reserved

   NOTE: Byte 3 of the packet is split into 2 and 6 bits
   NOTE: The upper part of the serial number should be in the range 0xA400 – 0xA41F
         The lower part of a serial number should be used in a manner it
         ensures uniqueness of the whole serial number
   NOTE: Maximum allowed length of a packet is 29B (together with separators 0x7E; 0xNF)

   Bytes 3 to 8 make up the message header. Depending on byte 3 [2bits] which
   is the packet type, there follow three different specifications (data, text, message)
   for the rest of the bytes of the packet.



'''


class JetiEx:

    def __init__(self):
        pass

