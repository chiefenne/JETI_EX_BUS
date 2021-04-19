
'''Function to calculate the CRC8 value of an EX packet

Description of the corresponding C code used by Jeti:
JETI_Telem_protocol_EN_V1.07.pdf

Test data from Jeti EX protocol. EX data specification on page 8 of
the protocol description:

    0x7E 0x9F 0x4C 0xA1 0xA8 0x5D 0x55 0x00 0x11 0xE8 0x23 0x21 0x1B 0x00 0xF4

Above data written in hex string format:
    hexstr = '7E 9F 4C A1 A8 5D 55 00 11 E8 23 21 1B 00 F4'

Hex string converted to bytes via bytearray.fromhex(hexstr)
    data = b'~\x9fL\xa1\xa8]U\x00\x11\xe8#!\x1b\x00\xf4'

The last byte above contains the checksum of the packet.

'''


def crc8(data : bytearray, offset, crc=0):
    '''CRC check (8-bit)
    CRC polynomial: X^8 + X^2 + X + 1 */
    poly = b'0x07'

    Args:
        data (bytearray): EX packet
        offset (int): start of packet
        length (int): length of packet

    Returns:
        int: checksum
    '''

    g = 1 << offset | b'0x07'  # Generator polynomial

    # Loop over the data
    for d in data:

        # XOR the top byte in the CRC with the input byte
        crc ^= d << (offset - 8)

        # Loop over all the bits in the byte
        for _ in range(8):
            # Start by shifting the CRC, so we can check for the top bit
            crc <<= 1

            # XOR the CRC if the top bit is 1
            if crc & (1 << offset):
                crc ^= g

    # Return the CRC value
    return crc


if __name__ == '__main__':

    # test with a packet from the documatation
