'''Function to calculate the CRC8 value of an EX packet

Description of the corresponding C code used by Jeti:
JETI_Telem_protocol_EN_V1.07.pdf

Test data from Jeti EX protocol. EX data specification on page 8 of
the protocol description.

Bitwise HEX manipulation:
https://stackoverflow.com/a/11119660/2264936

'''


def update_crc(crc_element, crc_seed):
    
    POLY = 0x07

    crc_u = crc_element
    crc_u ^= crc_seed

    for i in range(8):

        # C ternery operation --> condition ? value_if_true : value_if_false
        #  crc_u = (crc_u & 0x80) ? POLY ^ (crc_u << 1) : (crc_u << 1)
        # Python ternery operation --> a if condition else b
        crc_u = POLY ^ (crc_u << 1) if (crc_u & 0x80) else (crc_u << 1)

    return crc_u

def crc8(packet):
    
    crc_up = 0

    for i in range(0, len(packet)):
        crc_intermediate = update_crc(packet[i], crc_up)
        crc_up = copy.deepcopy(crc_intermediate)
   
    return hex(crc_up)[-2:].upper()


if __name__ == '__main__':

    # Run a test on the Jeti EX telemetry examples
    # Counting of checksum value begins at the third byte of the message (length of data)

    # data telemetry example (without separators 0x7E, 0x9F and crc value 0xF4)
    packet = [0x4C, 0xA1, 0xA8, 0x5D, 0x55, 0x00, 0x11, 0xE8,
                  0x23, 0x21, 0x1B, 0x00]

    crc = crc8(packet)

    print('Jeti CRC8 value:', crc)
    print('Expected result:', 'F4')

    # text telemetry example
    packet = [0x0F, 0xA1, 0xA8, 0x5D, 0x55, 0x00, 0x02,
                  0x2A, 0x54, 0x65, 0x6D, 0x70, 0x2E, 0xB0, 0x43]

    crc = crc8(packet)

    print('Jeti CRC8 value:', crc)
    print('Expected result:', '28')
