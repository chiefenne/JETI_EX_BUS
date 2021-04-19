
'''Function to calculate the CRC8 value of an EX packet

Description of the corresponding C code used by Jeti:
JETI_Telem_protocol_EN_V1.07.pdf

Test data from Jeti EX protocol. EX data specification on page 8 of
the protocol description:

    0x7E 0x9F 0x4C 0xA1 0xA8 0x5D 0x55 0x00 0x11 0xE8 0x23 0x21 0x1B 0x00 0xF4

The last byte above contains the checksum of the packet.

# format need by the crc16 function below
data = b'\x3D\x01\x08\x06\x3A\x00'

'''


def crc8(data : bytearray, offset , length):
    '''CRC check (8-bit)
    CRC polynomial: X^8 + X^2 + X + 1 */

    Args:
        data (bytearray): packet of the ex bus
        offset (int): start of packet
        length (int): length of packet

    Returns:
        int: checksum
    '''

    if data is None or offset < 0 or offset > len(data) - 1 and \
        offset+length > len(data):
        return 0
 
    crc = 0
    for i in range(0, length):
        crc ^= data[offset + i]
        for _ in range(0,8):
            if (crc & 1) > 0:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc = crc >> 1
    return crc
