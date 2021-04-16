
'''Function to calculate the CRC16-CCITT value of a packet

Description of the corresponding C code used by Jeti:
JETI EX Bus Protocol V.1.21 EN

Credits: Mark Adler
https://stackoverflow.com/a/67115933/2264936
    

Test data from Jeti Ex Bus protocol. Telemetry request from receiver (master)
Page 6 of the protocol description:

    0x3D 0x01 0x08 0x06 0x3A 0x00 0x98 0x81

The last two bytes above contain the checksum of the packet in the
order LSB and MSB. So those need to be swapped to make up the checksum,
i.e. 0x8198

# format need by the crc16 function below
data = b'\x3D\x01\x08\x06\x3A\x00'

'''


def crc16(data : bytearray, offset , length):
    '''CRC check using the CRC16-CCITT algorithm

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


if __name__ == '__main__':

    '''Do a demo of the crc16 function on a telemetry request packet
    
    Complete packet:
        0x3D 0x01 0x08 0x06 0x3A 0x00 0x98 0x81
    
    Packet without CRC:
        0x3D 0x01 0x08 0x06 0x3A 0x00

    CRC for that packet:
        0x8198
    '''
    hex_string = '3D 01 08 06 3A 00'
    data_bytes = bytearray.fromhex(hex_string)
    # data_bytes = b'\x3D\x01\x08\x06\x3A\x00'

    checksum = int(b'8198', 16)
    crc = crc16(data_bytes, 0, len(data_bytes))

    result = 'OK' if crc == checksum else 'NOTOK'

    print('CRC16-CCITT: ', crc16(data_bytes, 0, 6))
    print('   Checksum: ', checksum)
    print('      Check:  ' + result)

