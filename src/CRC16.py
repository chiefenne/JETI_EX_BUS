'''Function to calculate the CRC16-CCITT value of an EX bus packet

Description of the corresponding C code used by Jeti:
EX_Bus_protokol_v121_EN.pdf

The checksum starts at the first byte of the message (0x3B for Slave packet).

Test data from Jeti EX bus protocol.

Bitwise HEX manipulation:
https://stackoverflow.com/a/11119660/2264936

'''


def crc_ccitt_update(crc, data):
    
    data ^= crc & 0xFF
    data ^= data << 4

    ret_val = (((data << 8) | ((crc & FF00) >> 8)) \
                ^ (data >> 4) ^ (data << 3))

    return ret_val

def get_crc16z(packet):
    
    crc16_data = 0

    for i in range(len(packet)):
        crc16_data = crc_ccitt_update(crc16_data, packet[i])
   
    return crc16_data


if __name__ == '__main__':

    # Run a test on the Jeti EX bus telemetry examples

    # example EX telemetry
    packet = [0x3B, 0x01, 0x20, 0x08, 0x3A, 0x18, 0x9F, 0x56, 0x00, 0xA4, 0x51,
              0x55, 0xEE, 0x11, 0x30, 0x20, 0x21, 0x00, 0x40, 0x34, 0xA3, 0x28,
              0x00, 0x41, 0x00, 0x00, 0x51, 0x18, 0x00, 0x09]

    crc = get_crc16z(packet)

    print('Jeti CRC16-CCITT value:', crc)
    print('Expected result:', 'D691')

    # example Jetibox menu
    packet = [0x3B, 0x01, 0x28, 0x88, 0x3B, 0x20, 0x43, 0x65, 0x6E, 0x74, 0x72,
              0x61, 0x6C, 0x20, 0x42, 0x6F, 0x78, 0x20, 0x31, 0x30, 0x30, 0x3E,
              0x20, 0x20, 0x20, 0x34, 0x2E, 0x38, 0x56, 0x20, 0x20, 0x31, 0x30,
              0x34, 0x30, 0x6D, 0x41, 0x68]

    crc = get_crc16z(packet)

    print('Jeti CRC16-CCITT value:', crc)
    print('Expected result:', 'DEEB')
