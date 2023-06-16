'''Decode a Jeti EX packet'''

import struct
from binascii import hexlify


class ExPacketDecoder:

    def __init__(self, ex_packet=None):
        self.ex_packet = ex_packet

        # header types
        self.types = {0: 'Text', 1: 'Data', 2: 'Message'}

    def decode(self):
        '''Decode a Jeti EX packet'''

        # data identifier (two leftmost bits) and length of data blocks (6 rightmost bits)
        self.id_len = struct.unpack('b', self.ex_packet[0:1])[0]
        self.length = self.id_len & 0b00111111
        self.id = self.id_len >> 6
        self.product_id = self.ex_packet[2:4]
        self.device_id = self.ex_packet[4:6]
        if self.types[self.id] == 'Data':
            self._decode_data()
        elif self.types[self.id] == 'Text':
            self._decode_text()

    def _decode_data(self):
        self.teleid_dtype = struct.unpack('b', self.ex_packet[6:7])[0]
        self.teleid = self.teleid_dtype >> 4
        self.dtype = self.teleid_dtype & 0b00001111
        print('    Data type: {}'.format(self.dtype))

    def _decode_text(self):
        # telemtry identifier
        self.teleid = struct.unpack('b', self.ex_packet[6:7])[0]

        # length of description and unit
        self.len_desc_unit = struct.unpack('b', self.ex_packet[7:8])[0]
        self.len_desc = self.len_desc_unit >> 3
        self.len_unit = self.len_desc_unit & 0b00001111

        # description
        self.desc = self.ex_packet[8:8 + self.len_desc].decode('ascii')

        # unit
        self.unit = self.ex_packet[9 + self.len_desc:9 + self.len_desc + self.len_unit].decode('ascii')

    def _print(self):

        print('')
        print('  EX Packet:')
        print('    Data identifier: {}'.format(self.types[self.id]))
        print('    Length of data blocks: {}'.format(self.length))
        # product id (bytes are little endian) as integer
        print('    Product ID: {}'.format(int.from_bytes(self.product_id, 'little')))
        # device id (bytes are little endian) as integer
        print('    Device ID: {}'.format(int.from_bytes(self.device_id, 'little')))
        print('    Telemetry identifier: {}'.format(self.teleid))
        print('    Description: {}'.format(self.desc))
        print('    Unit: {}'.format(self.unit))
        print('    CRC8: {}'.format(self.crc8(self.ex_packet[:-1])))
        print('    CRC8 expected: {}'.format(hex(self.ex_packet[-1])[2:].upper()))

    def update_crc(self, crc_element, crc_seed):

        POLY = 0x07

        crc_u = crc_element
        crc_u ^= crc_seed

        for i in range(8):

            # C ternery operation --> condition ? value_if_true : value_if_false
            #  crc_u = (crc_u & 0x80) ? POLY ^ (crc_u << 1) : (crc_u << 1)
            # Python ternery operation --> a if condition else b
            crc_u = POLY ^ (crc_u << 1) if (crc_u & 0x80) else (crc_u << 1)

            # mask crc_u to 8 bits
            crc_u &= 0xFF

        return crc_u

    def crc8(self, ex_packet):

        crc_up = 0

        for i in range(0, len(ex_packet)):
            crc_up = self.update_crc(ex_packet[i], crc_up)

        return hex(crc_up)[-2:].upper()


if __name__ == '__main__':

    # example packets from the JETI documentation
    # without separators 0x7E, 0x9F
    # crc is 'F4' and is not used above in the crc8 function, only for comparison
    ex_packets = [bytearray(b'\x4C\xA1\xA8\x5D\x55\x00\x11\xE8\x23\x21\x1B\x00\xF4'),
                  bytearray(b'\x10\x00\xa4\x01\x00\x00\x00@MHBVario\x8f')]

    # decode the packets
    ex_decoder = ExPacketDecoder()
    for ex_packet in ex_packets:
        ex_decoder.ex_packet = ex_packet
        ex_decoder.decode()
        ex_decoder._print()
