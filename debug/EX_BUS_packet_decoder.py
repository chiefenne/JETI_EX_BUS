'''Decode a Jeti EX BUS packet'''

import struct
from binascii import hexlify


class ExBusPacketDecoder:

    def __init__(self, packet=None):
        self.packet = packet

    # Packet Identifier
        self.packet_header = {
            b'\x3E': "Master Packet",
            b'\x3D': "Master Packet",
            b'\x3B': "Slave Packet"
        }

        # Data Identifier
        self.data_identifiers = {
            (b'\x3E', b'\x31'): "Channel Values",
            (b'\x3D', b'\x3A'): "Telemetry request",
            (b'\x3D', b'\x3B'): "JETIBOX request",
            (b'\x3B', b'\x3A'): "EX Telemetry",
            (b'\x3B', b'\x3B'): "JETIBOX menu"
        }

    def decode(self):
        '''Decode a Jeti EX BUS packet'''

        # unpack the packet
        self.header = hexlify(self.packet[0:1])
        self.source = self.packet_header[bytes(self.packet[0:1])]
        self.message_length = struct.unpack('b', self.packet[2:3])[0]
        self.packet_id = struct.unpack('b', self.packet[3:4])[0]
        self.data_identifier = bytes(self.packet[4:5])
        self.type = self.data_identifiers[(bytes(self.packet[0:1]), self.data_identifier)]
        self.length_data = struct.unpack('b', self.packet[5:6])[0]
        self.data = self.packet[6:-2]

        # reverse the CRC bytes as it comes with LSB first
        self.crc = int.from_bytes(self.packet[-2:], 'little')

    def getChannelData(self):

        self.channel = dict()
        for i in range(0, self.length_data, 2):
            channel = self.data[i:i+1] + self.data[i+1:i+2]
            self.channel[i/2] = int.from_bytes(channel, 'little') / 8000

    def _print(self):
        '''Print the decoded packet'''

        print('')
        print('EX BUS Packet:')
        print('  Header (source): {}'.format(self.source))
        print('  Message length: {}'.format(self.message_length))
        print('  Packet ID: {}'.format(self.packet_id))
        print('  Data identifier: {}'.format(self.type))
        print('  Length of data blocks: {}'.format(self.length_data))

        # check for chnnel data
        if self.type == 'Channel Values':
            self.getChannelData()
            print('  Channel Values:')
            for i in range(len(self.channel)):
                print('    Channel {}: {}'.format(i+1, self.channel[i]))

        print('  CRC: {}'.format(self.crc))
        print('  CRC expected: {}'.format(self.crc16_ccitt(self.packet[:-2])))

    def crc16_ccitt(self, data : bytearray):
        '''Calculate the CRC16-CCITT value from data packet.
        Args:
            data (bytearray): Jeti EX bus packet
        Returns:
            int: CRC16-CCITT value

        NOTE: removed offset (see link below) as we start from 1st byte

        Credits: Mark Adler https://stackoverflow.com/a/67115933/2264936
        '''
        crc = 0
        for i in range(0, len(data)):
            crc ^= data[i]
            for j in range(0,8):
                if (crc & 1) > 0:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc = crc >> 1

        return crc

if __name__ == '__main__':

    # example packets from the JETI documentation
    packets = [bytearray(b'\x3E\x03\x28\x06\x31\x20\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x82\x1F\x4F\xE2'),
               bytearray(b'\x3D\x01\x08\x06\x3A\x00\x98\x81'),
               bytearray(b'\x3D\x01\x09\x88\x3B\x01\xF0\xA3\x24'),
               bytearray(b'\x3B\x01\x20\x08\x3A\x18\x9F\x56\x00\xA4\x51\x55\xEE\x11\x30\x20\x21\x00\x40\x34\xA3\x28\x00\x41\x00\x00\x51\x18\x00\x09\x91\xD6'),
               bytearray(b'\x3B\x01\x28\x88\x3B\x20\x43\x65\x6E\x74\x72\x61\x6C\x20\x42\x6F\x78\x20\x31\x30\x30\x3E\x20\x20\x20\x34\x2E\x38\x56\x20\x20\x31\x30\x34\x30\x6D\x41\x68\xEB\xDE'),
               bytearray(b'\x3B\x01\x23\x00\x3A\x1b\x0f\x13\x00\xa4\x01\x00\x00\x00\x3A\x4d\x48\x42\x56\x61\x72\x69\x6f\x5E\xa6\x3b'),
               bytearray(b';\x01\x1b\x00:\x13\x0f\x0b\x00\xa4\x01\x00\x00\x00@MHBVarioB9?o')]

    # decode the packets
    decoder = ExBusPacketDecoder()
    for packet in packets:
        decoder.packet = packet
        decoder.decode()
        decoder._print()
