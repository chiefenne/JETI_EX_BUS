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


    packet = []

    crc = get_crc16z(packet)

    print('Jeti CRC16-CCITT value:', crc)
    print('Expected result:', '')

    # text telemetry example
    packet = []

    crc = get_crc16z(packet)

    print('Jeti CRC16-CCITT value:', crc)
    print('Expected result:', '')
