'''Function to calculate the CRC16-CCITT value of an EX bus packet

Description of the corresponding C code used by Jeti:
EX_Bus_protokol_v121_EN.pdf

The checksum starts at the first byte of the message (0x3B for Slave packet).
'''

import micropython


@micropython.viper
def crc16_ccitt(packet:ptr8, length: int) -> int:
    '''Calculate the CRC16-CCITT value from data packet.'''
    crc = 0
    for i in range(length):
        crc ^= packet[i]
        for j in range(8):
            if (crc & 1) > 0:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc = crc >> 1

    return crc


if __name__ == '__main__':
    '''Run a test on the Jeti EX bus checksum examples.
    
       The packet needs to be checked without the CRC values, i.e., the last
       two bytes of the packet.
    '''

    # example receiver (master) sends channel data (EX_Bus_protokol_v121_EN.pdf, page 6)
    packet = [0x3E, 0x03, 0x28, 0x06, 0x31, 0x20, 0x82, 0x1F, 0x82, 0x1F, 0x82,
              0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F,
              0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82, 0x1F, 0x82,
              0x1F, 0x82, 0x1F, 0x82, 0x1F]

    crc_int = crc16_ccitt(packet, len(packet))
    crc = hex(crc_int)[2:]

    print('')
    print('Example receiver (master) sends channel data:')
    print('CRC16 value:', crc)
    print('Expected result:', 'E24F')
    print('')

    # example receiver (master) sends telemetry request (EX_Bus_protokol_v121_EN.pdf, page 6)
    packet = [0x3D, 0x01, 0x08, 0x06, 0x3A, 0x00]

    crc_int = crc16_ccitt(packet, len(packet))
    crc = hex(crc_int)[2:]

    print('')
    print('Example receiver (master) sends telemetry request:')
    print('CRC16 value:', crc)
    print('Expected result:', '8198')
    print('')

    # example EX telemetry (EX_Bus_protokol_v121_EN.pdf, page 7)
    packet = [0x3B, 0x01, 0x20, 0x08, 0x3A, 0x18, 0x9F, 0x56, 0x00, 0xA4, 0x51,
              0x55, 0xEE, 0x11, 0x30, 0x20, 0x21, 0x00, 0x40, 0x34, 0xA3, 0x28,
              0x00, 0x41, 0x00, 0x00, 0x51, 0x18, 0x00, 0x09]

    crc_int = crc16_ccitt(packet, len(packet))
    crc = hex(crc_int)[2:]

    print('')
    print('Example sensor (slave) sends telemetry data:')
    print('CRC16 value:', crc)
    print('Expected result:', 'D691')
    print('')

    # example Jetibox menu (EX_Bus_protokol_v121_EN.pdf, page 7)
    packet = [0x3B, 0x01, 0x28, 0x88, 0x3B, 0x20, 0x43, 0x65, 0x6E, 0x74, 0x72,
              0x61, 0x6C, 0x20, 0x42, 0x6F, 0x78, 0x20, 0x31, 0x30, 0x30, 0x3E,
              0x20, 0x20, 0x20, 0x34, 0x2E, 0x38, 0x56, 0x20, 0x20, 0x31, 0x30,
              0x34, 0x30, 0x6D, 0x41, 0x68]

    crc_int = crc16_ccitt(packet, len(packet))
    crc = hex(crc_int)[2:]

    print('')
    print('Example sensor (slave) sends Jetibox menu:')
    print('CRC16 value:', crc)
    print('Expected result:', 'DEEB')
    print('')
