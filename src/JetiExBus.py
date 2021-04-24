'''Python Implementation of the JETI EX Bus protocol


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
from ubinascii import hexlify

import crc16_ccitt
import Logger
import Streamrecorder


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

        self.telemetry = bytearray()

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
        '''This is the main loop and will run forever. This function is called
        at the end of the function "main.py". It does exactly the same as the
        Arduino "loop()" function.

        Within the loop the datastream of the EX bus checked for:
          1) Channel data (current status of the transmitter)
          2) Telemetry request (a sensor can send data)
          3) JetiBox request (modify parameters)
        '''
        self.request_telemetry = False
        self.request_JetiBox = False
        self.received_channels = False

        while True:

            # for debugging only (see module Streamrecorder for usage)
            # change record variable below to "True" to record the serial stream
            # it will be written to a text file on the SD card
            # when "True" is set, only stream recording is done (break)
            # filename and recording duration can be specified
            record = False
            if record:
                Streamrecorder.saveStream(self.serial, logger,
                                     filename='EX_Bus_stream.txt',
                                     duration=1000)
                break

            # check serial stream for data
            # be careful with "any" (see MP docs)
            if self.serial.any() == 0:
                continue

            # read 5 bytes to be able to check for (channel, telemetry or JetiBox)
            self.start_packet = self.serial.read(5)

            # check for telemetry request and send data if needed
            if self.checkTelemetryRequest():
                self.sendTelemetryData()
                # FIXME remove break after testing
                break

            # check for JetiBox request and send data if needed
            if self.checkJetiBoxRequest():
                self.sendJetiBoxData()
                # FIXME remove break after testing
                break

            # check for channel data and read them if available
            if self.checkTelemetryRequest():
                self.getChannelData()
                # FIXME remove break after testing
                break
    
    def checkTelemetryRequest(self):
        '''Check if a telemetry request was sent by the master (receiver)
        '''
        # telemetry request starts with '3D01' and 5th byte is '3A'
        # so the check is: b[0:2] == b'=\x01' and b[4:5] == b':'
        if self.start_packet[0:2] == b'=\x01' and \
                self.start_packet[4:5] == b':':
            self.logger.log('debug', 'Found Ex Bus telemetry request')
            self.request_telemetry = True
            return True

        return False

    def checkJetiBoxRequest(self):
        '''Check if a JetiBox request was sent by the master (receiver)
        '''
        # JetiBox request starts with '3D01' and 5th byte is '3B'
        # so the check is: b[0:2] == b'=\x01' and b[4:5] == b';'
        if self.start_packet[0:2] == b'=\x01' and \
                self.start_packet[4:5] == b';':
            self.logger.log('debug', 'Found Ex Bus JetiBox request')
            self.request_JetiBox = True
            return True

        return False

    def checkChannelData(self):
        '''Check if channel data were sent by the master (receiver)
        '''
        # channel data packet starts with '3E03' and 5th byte is '31'
        # so the check is: b[0:2] == b'=\x01' and b[4:5] == b'1'
        if self.start_packet[0:2] == b'>\x03' and \
                self.start_packet[4:5] == b'1':
            self.logger.log('debug', 'Found Ex Bus channel data')
            self.received_channels = False
            return True

        return False

    def sendTelemetryData(self):
        '''[summary]
        '''

        self.telemetry.extend()
        
        # compose and write packet
        # bytes_written = self.serial.write(packet)
        pass

    def sendJetiBoxData(self):
        pass

    def getChannelData(self):
        pass

    def getSensors(self, i2c):
        '''Get I2C sensors attached to the board.

        Args:
            i2c (I2C_Sensors instance): carries all hardware connected via I2c
        '''
        self.sensors = i2c.sensors

    def readPacket(self, identifier='channel'):
        '''Read one full Jeti EX bus packet (from header to CRC)

        Args:
            identifier (str): One of 'channel', 'telemetry', 'jetibox' 

        Returns:
            byte: Returns one complete Jeti ex bus packet
        '''

        packet = None

        return packet

    def writePacket(self, identifier='telemetry'):
        '''Write one full Jeti EX bus packet (from header to CRC)

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
        crc = self.readPacket(packet)

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
        '''Function to deconnect from the serial connection.
        (Most likely not used in this application)
        '''
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
