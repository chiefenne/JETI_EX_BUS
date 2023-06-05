'''Decode a Jeti EX packet'''

import struct
from binascii import hexlify


class ExPacketDecoder:

    def __init__(self, packet=None):
        self.packet = packet

        # header types
        self.types = {0: 'Text', 1: 'Data', 2: 'Message'}

    def decode(self):
        '''Decode a Jeti EX packet'''

        # packet identifier
        self.packet_id = struct.unpack('b', self.packet[0:1])[0]

        # data identifier (two leftmost bits) and length of data blocks (6 rightmost bits)
        self.id_len = struct.unpack('b', self.packet[1:2])[0]
        self.length = self.id_len & 0b00111111
        self.id = self.id_len >> 6
        self.product_id = self.packet[2:4]
        self.device_id = self.packet[4:6]
        self.datatype = self.packet[4:5]
        # length of description (5 leftmost bytes) and length of data (3 rightmost bytes)
        self.len_desc_data = struct.unpack('b', self.packet[8:9])[0]
        self.len_desc = self.len_desc_data >> 3
        self.len_data = self.len_desc_data & 0b00000111
        self.desc = self.packet[9:9+self.len_desc]
        self.unit = self.packet[9+self.len_desc:9+self.len_desc+self.len_data]

    def _print(self):

        print('')
        print('EX Packet:')
        print('  Packet ID: {} {}'.format(hex(self.packet_id), self.packet_id))
        print('  Data identifier: {}'.format(self.types[self.id]))
        print('  Length of data blocks: {}'.format(self.length))
        # product id (bytes are little endian) as integer
        print('  Product ID: {}'.format(int.from_bytes(self.product_id, 'little')))
        # device id (bytes are little endian) as integer
        print('  Device ID: {}'.format(int.from_bytes(self.device_id, 'little')))
        print('  Length of description: {}'.format(self.len_desc))
        print('  Length of unit: {}'.format(self.len_data))
        print('  Description: {}'.format(self.desc.decode('utf-8')))
        print('  Unit: {}'.format(self.unit.decode('utf-8')))
        print('  CRC8: {}'.format(self.crc8(self.packet[1:-2])))
        print('  CRC expected: {}'.format(self.packet[-2:].decode()))

    def update_crc(self, crc_element, crc_seed):

        POLY = 0x07

        crc_u = crc_element
        crc_u ^= crc_seed

        for i in range(8):

            # C ternery operation --> condition ? value_if_true : value_if_false
            #  crc_u = (crc_u & 0x80) ? POLY ^ (crc_u << 1) : (crc_u << 1)
            # Python ternery operation --> a if condition else b
            crc_u = POLY ^ (crc_u << 1) if (crc_u & 0x80) else (crc_u << 1)

        return crc_u

    def crc8(self, packet):

        crc_up = 0

        for i in range(0, len(packet)):
            crc_up = self.update_crc(packet[i], crc_up)
    
        return hex(crc_up)[-2:].upper()


if __name__ == '__main__':

    # example packets from the JETI documentation
    packets = [bytearray(b'\x0f\x0b\x00\xa4\x01\x00\x00\x00@MHBVarioB9')]

    # decode the packets
    decoder = ExPacketDecoder()
    for packet in packets:
        decoder.packet = packet
        decoder.decode()
        decoder._print()
