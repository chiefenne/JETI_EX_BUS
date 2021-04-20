'''Python Implementation of the JETI Ex Bus protocol


Implementation via MicroPython (Python for microprocessors):
    https://micropython.org/
    https://github.com/micropython/micropython    


JETI Ex Bus specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/
    
    File: EX_Bus_protokol_v121_EN.pdf

Ex Bus protocol description:
============================

1) Packet (8 bytes) with the telemetry request sent by the receiver (master)

    Byte | Length |     Data     |  Description
   ------|--------|--------------|----------------------------------------
     1   |    1   |     0x3D     |  Header
     2   |    1   |     0x01     |  Header
     3   |    1   |      LEN     |  Message length incl. CRC
     4   |    1   |       ID     |  Packet ID
     5   |    1   |     0x3A     |  Identifier for a telemetry request
     6   |    1   |        0     |  Length of data block
    7/8  |    2   |    CRC16     |  CRC16-CCITT in sequence LSB, MSB             |

   NOTE: - slave needs to answer with this Packet ID (byte 4)
         - LSB, MSB need to be swapped to get the checksum
         - byte 1 (0x3D) states that this is a request
         - byte 2 (0x01) states that after this packet there is a 4ms slot on
           the ex bus to answer with the corresponding information
         - byte 5 (0x3A) states that this is a telemetry request

2) Packet (9 bytes) with the JetiBox request sent by the receiver (master)
   There is only little difference to the telemerty request:

    Byte | Length |     Data     |  Description
   ------|--------|--------------|----------------------------------------
     5   |    1   |     0x3B     |  Identifier for a JetiBox request
     7   |    1   |  0bLDUR0000  |  Information of the buttons

          
Some important characters in the ex bus protocol:
    hex string '3A' maps to binary b':'
    hex string '3B' maps to binary b';'
    hex string '3D' maps to binary b'='
    hex string '3E' maps to binary b'>'
    hex string '01' maps to binary b'\x01'


Author: Dipl.-Ing. A. Ennemoser
Date: 14-04-2021
Version: 0.2

Changes:
    Version 0.2 - 17-04-2021: basic structure of the code established
    Version 0.1 - 14-04-2021: initial version of the implementation

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from machine import UART
import ubinascii
import usys
import uos
import utime
import uasyncio

import crc16_ccitt
import Logger

# setup a logger for the REPL
logger = Logger.Logger()


class JetiExBus:
    '''JETI Ex Bus protocol handler
    Allows to connect to sensors via serial cpmmunication (UART)

    JETI uses 125kbaud or 250kbaud. The speed is prescribed by the
    receiver (master). The speed has to be checked by the sensor (slave)
    via the CRC check (see checkSpeed)

    '''

    def __init__(self, baudrate=125000, bits=8, parity=None, stop=1, port=3):
        self.serial = None

        # Jeti ex bus protocol runs 8-N-1, speed any of 125000 or 250000
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.port = port

        self.buffer = bytearray()

        # setup a logger for the REPL
        self.logger = Logger.Logger()


    def connect(self):
        '''Setup the serial conection via UART
        JETI uses 125kbaud or 250kbaud. The speed is prescribed by the
        receiver (master). The speed has to be checked by the sensor (slave)
        via the CRC check (see checkSpeed))
        '''

        self.serial = UART(self.port, self.baudrate)
        self.serial.init(baudrate=self.baudrate,
                         bits=self.bits,
                         parity=self.parity,
                         stop=self.stop)

    def run_forever(self):

        self.request_telemetry = False
        self.request_JetiBox = False
        self.received_channels = False

        while True:

            # check if there are any data available
            if self.serial.any() == 0:
                continue

            # for debugging only
            if True:
                self.getStream()
                break

            # read 5 bytes to be able to check for (channel, telemetry or JetiBox)
            self.start_packet = self.serial.read(5)

            # ex bus telemetry request starts with '3D01' and 5th byte is '3A'
            # so the check is: b[0:2] == b'=\x01' and b[4:5] == b':'
            if self.start_packet[0:2] == b'=\x01' and \
                    self.start_packet[4:5] == b':':
                self.logger.log('debug', 'Found Ex Bus telemetry request')
                self.request_telemetry = True
                # self.handleTelemetryRequest()
                break

            # ex bus JetiBox request starts with '3D01' and 5th byte is '3B'
            # so the check is: b[0:2] == b'=\x01' and b[4:5] == b';'
            if self.start_packet[0:2] == b'=\x01' and \
                    self.start_packet[4:5] == b';':
                self.logger.log('debug', 'Found Ex Bus JetiBox request')
                self.request_JetiBox = True
                #self.handleJetiboxRequest()
                break

            # ex bus channel data packet starts with '3E03' and 5th byte is '31'
            # so the check is: b[0:2] == b'=\x01' and b[4:5] == b'1'
            if self.start_packet[0:2] == b'>\x03' and \
                    self.start_packet[4:5] == b'1':
                self.logger.log('debug', 'Found Ex Bus channel data')
                self.received_channels = False
                # self.handleChannnelData()
                break

    def getStream(self):
        self.packet = bytearray(20000)
        start = utime.ticks_ms()
        time = 0
        while time < 1000:
            self.packet += self.serial.read()
            message = 'Packet length is {}'.format(len(self.packet))
            self.logger.log('debug', message)
            time = utime.ticks_diff(time, start)

    def handleTelemetryRequest(self):
        '''Fill frame buffer with ex bus data
        '''

        hex_request = ''

        # read one character from serial stream
        self.buffer = self.serial.read(1)

        hexstr = ubinascii.hexlify(self.buffer)
        self.logger.log('debug', str(self.buffer))

        # check for ex bus packet header (0x3E or 0x3D)
        if hexstr == b'3d':

            # read and add following 7 bytes of the stream
            self.buffer = self.buffer + self.serial.read(7)
            hex_request = ubinascii.hexlify(self.buffer)

            message = 'Got request {}'.format(self.buffer)
            self.logger.log('info', message)
            message = 'Type self.buffer {}'.format(type(self.buffer))
            self.logger.log('info', message)

            message = 'Hexlified request {}'.format(
                ubinascii.hexlify(self.buffer))
            self.logger.log('info', message)

            # for a telemetry request from the master (receiver) the first
            # three bytes have to be '3d0108' and the 5th byte hast to be '3a'
            if b'3d0108' in hex_request and b'3a' in hex_request:
                self.telemetry_request = True

            # send telemetry data
            self.sendTelemetry()
    
    def sendTelemetry(self):
        
        # compose and write packet
        # bytes_written = self.serial.write(packet)
        pass

    def handleJetiboxRequest(self):
        pass

    def handleChannnelData(self):
        pass

    def readPacket(self, identifier='channel'):
        '''Read one full Jeti ex bus packet (from header to CRC)

        Args:
            identifier (str): One of 'channel', 'telemetry', 'jetibox' 

        Returns:
            byte: Returns one complete Jeti ex bus packet
        '''

        packet = None

        return packet

    def writePacket(self, identifier='telemetry'):
        '''Write one fule Jeti ex bus packet (from header to CRC)

        Args:
            identifier (str): One of 'telemetry' or 'jetibox'
        '''
        
        packet = None

        return packet

    def checkSpeed(self):
        '''Check the connection speed via CRC. This needs to be done by
        the sensor (slave). The speed is either 125000 (default) or 250000
            - if CRC ok, then speed is ok
            - if CRC is not ok, then speed has to be set to the
              respective 'other' speed

        Args:
            packet (bytes): one complete packet received from the
                            Jeti receiver (master)

        Returns:
            bool: information if speed check was ok or failed
        '''

        packet = self.readPacket('channel')

        # do a CRC check on a Jeti ex bus packet
        crc = self.CRC(packet)

        speed_changed = False

        # change speed if CRC check fails
        if not crc:
            speed_changed = True
            if self.baudrate == 125000:
                self.baudrate = 250000
            elif self.baudrate == 250000:
                self.baudrate = 125000

        return speed_changed

    def deconnect(self):
        self.serial.deinit()

    def checkCRC(self, packet):
        '''Do a CRC check using CRC16-CCITT

        Args:
            packet (bytearray): packet of Jeti Ex Bus including the checksum
                                The last two bytes of the packet are LSB and
                                MSB of the checksum. 

        Returns:
            bool: True if the crc check is OK, False if NOT
        '''
        crc_ok = crc16_ccitt.crc16(packet, 0, len(packet))

        return crc_ok
