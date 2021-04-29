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



Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from machine import UART
from ubinascii import hexlify

import crc16_ccitt
import Logger
import Streamrecorder
import bme280_float as bme280
import JetiEx


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

        # instantiate the EX protocol
        self.jetiex = JetiEx.JetiEx()

        self.telemetry = bytearray()
        self.send_sensor = True

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

        Within the loop the datastream of the EX bus is checked for:
          1) Telemetry request (a sensor can send data)
          2) JetiBox request (modify parameters)
          3) Channel data (current status of the transmitter)
        '''

        while True:

            # check serial stream for data
            # be careful with "any" (see MP docs)
            if self.serial.any() == 0:
                continue

            # check for (channel, telemetry or JetiBox)
            self.exbus = self.serial.read(8)

            # check for telemetry request and send data if needed
            self.checkTelemetryRequest()

            # check for JetiBox menu request and send data if needed
            self.checkJetiBoxRequest()

            # check for channel data and read them if available
            self.checkChannelData()

            # endless loop continues here
    
    def checkTelemetryRequest(self):
        '''Check if a telemetry request was sent by the master (receiver)
        '''

        telemetry_request = self.exbus[0:2] == b'=\x01' and \
                            self.exbus[4:5] == b':'

        if telemetry_request:
            self.sendTelemetry()
            return True

        return False

    def checkJetiBoxRequest(self):
        '''Check if a JetiBox menu request was sent by the master (receiver)
        '''
        # JetiBox request starts with '3D01' and 5th byte is '3B'
        # so the check is: b[0:2] == b'=\x01' and b[4:5] == b';'
        jetibox_request = self.exbus[0:2] == b'=\x01' and \
                          self.exbus[4:5] == b';'

        # 1 byte missing for whole telemetry packet (we read 8 bytes so far)
        self.exbus.extend(self.serial.read(1))

        if jetibox_request:
            self.sendJetiBoxMenu()
            return True

        return False

    def checkChannelData(self):
        '''Check if channel data were sent by the master (receiver)
        '''
        # channel data packet starts with '3E03' and 5th byte is '31'
        # so the check is: b[0:2] == b'=\x01' and b[4:5] == b'1'
        channels_available = self.exbus[0:2] == b'>\x03' and \
                             self.exbus[4:5] == b'1'

        # read remaining bytes (we read 8 bytes so far)
        # FIXME
        # FIXME  calculate correct number of remaining bytes
        # FIXME
        r_bytes = 10
        self.exbus.extend(self.serial.read(r_bytes))

        if channels_available:
            self.getChannelData()
            return True

        return False

    def sendTelemetry(self):
        '''Send telemetry data back to the receiver. Each call of this function
        sends data from the next sensor or data type in the queue.
        '''

        # toggles True and False
        self.send_sensor ^= True
        
        if self.send_sensor:
            # get next sensor to send its data
            sensor = next(self.next_sensor)
        else:     
            # get next message type ('data' or 'text')
            packet_type = next(self.next_packet_type)
        
        packet = self.jetiex.Packet(sensor, packet_type)

        # write packet to the EX bus stream
        self.serial.write(packet)

    def sendJetiBoxMenu(self):
        pass

    def getChannelData(self):
        pass

    def Sensors(self, i2c_sensors):
        '''Get I2C sensors attached to the board
            i2c (I2C_Sensors instance): carries all hardware connected via I2c

        Args:
            i2c_sensors (JetiSensor object): Sensor meta data (id, type, address, driver, etc.)
        '''
        self.jetiex.Sensors(i2c_sensors)

        # generator object to be able to cycle through sensors
        self.next_sensor = self.round_robin(i2c_sensors.available_sensors.keys())

        # generator object to be able to cycle through sensor data and sensor text
        self.next_message = self.round_robin(['data', 'text'])

    def round_robin(self, cycled_list):
        '''Light weight implementation for cycling periodically through lists
        Source: https://stackoverflow.com/a/36657230/2264936
        
        Args:
            sensors (list): Any list which should be cycled
        Yields:
            Next element in the list
        '''
        while cycled_list:
            for element in cycled_list:
                yield element

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

        # do the same as in run_forever
        while True:
            self.exbus = self.serial.read(5)
            self.checkTelemetryRequest()
            if self.request_telemetry:
                pass
        
        # EX bus CRC starts with first byte of the packet
        offset = 0
        
        # packet to check is message without last 2 bytes
        packet = bytearray(self.telemetryRequest[:-2])

        # the last 2 bytes of the message makeup the crc value for the packet
        packet_crc = self.telemetryRequest[-2:]

        # calculate the crc16-ccitt value of the packet
        crc = crc16_ccitt.crc16(packet, offset, len(packet))

        if crc == packet_crc:
            speed_changed = False
        else:
            # change speed if CRC check fails
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
