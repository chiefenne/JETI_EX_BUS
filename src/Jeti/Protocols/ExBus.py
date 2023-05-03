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
from ubinascii import hexlify, unhexlify
import utime

import CRC16
import Logger
import Streamrecorder
from Ex import Ex


class ExBus:
    '''JETI Ex Bus protocol handler
    Allows to connect to sensors via serial cpmmunication (UART)

    JETI uses 125kbaud or 250kbaud. The speed is prescribed by the
    receiver (master). The speed has to be checked by the sensor (slave)
    via the CRC check (see checkSpeed)

    '''

    def __init__(self, baudrate=125000, bits=8, parity=None, stop=1, port=3):
        self.serial = None
        self.exbus = bytearray()

        # Jeti ex bus protocol runs 8-N-1, speed any of 125000 or 250000
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.port = port

        # instantiate the EX protocol
        self.ex = Ex()

        self.telemetry = bytearray()
        self.get_new_sensor = False

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
            characters = self.serial.read(8)
            self.exbus.extend(characters)

            # check for telemetry request and send data if needed
            self.checkTelemetryRequest()

            # check for JetiBox menu request and send data if needed
            # self.checkJetiBoxRequest()

            # check for channel data and read them if available
            # self.checkChannelData()

            # reset
            self.exbus = bytearray()

            # endless loop continues here
    
    def checkTelemetryRequest(self):
        '''Check if a telemetry request was sent by the master (receiver)
        '''

        telemetry_request = self.exbus[0:2] == b'=\x01' and \
                            self.exbus[4:5] == b':'


        if telemetry_request:
            # packet ID is used to link request and telemetry answer
            packet_ID = self.exbus[4]
            self.sendTelemetry(packet_ID)
            return True

        return False

    def checkJetiBoxRequest(self):
        '''Check if a JetiBox menu request was sent by the master (receiver)
        '''
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
        channels_available = self.exbus[0:2] == b'>\x03' and \
                             self.exbus[4:5] == b'1'

        # read remaining bytes (we read 8 bytes so far)
        # FIXME
        # FIXME  calculate correct number of remaining bytes
        # FIXME
        r_bytes = 10
        characters = self.serial.read(r_bytes)
        self.exbus += characters

        if channels_available:
            self.getChannelData()
            return True

        return False

    def sendTelemetry(self, packet_ID):
        '''Send telemetry data back to the receiver. Each call of this function
        sends data from the next sensor or data type in the queue.
        '''

        # compile the complete EX bus packet
        exbus_packet = self.ExBusPacket(packet_ID)

        # FIXME        
        # FIXME check for uneven number and if it matters at all        
        # FIXME        
        if len(exbus_packet) % 2 == 1:
            return

        # write packet to the EX bus stream
        # bytes_written = self.serial.write(exbus_packet)
        # bytes_written = self.serial.write(unhexlify(exbus_packet))
        start = utime.ticks_us()
        bytes_written = self.serial.write(exbus_packet)
        end = utime.ticks_us()
        diff = utime.ticks_diff(end, start)
        #print('Time for answer:', diff / 1000., 'ms')

        # failed to write to serial stream
        if bytes_written is None:
            print('NOTHING WAS WRITTEN')

    def ExBusPacket(self, packet_ID):

        self.exbus_packet = bytearray()

        # toggles True and False
        self.get_new_sensor ^= True
        
        # send data and text messages for each sensor alternating
        if self.get_new_sensor:
            # get next sensor to send its data
            self.current_sensor = next(self.next_sensor)
            current_EX_type = 'data'
        else:     
            current_EX_type = 'text'
        
        # get the EX packet for the current sensor
        ex_packet = self.ex.ExPacket(self.current_sensor, current_EX_type)

        # EX bus header
        self.exbus_packet.extend(b'3B01')

        # EX bus packet length in bytes including the header and CRC
        exbus_packet_length = 8 + len(ex_packet)
        self.exbus_packet.extend('{:02x}'.format(exbus_packet_length))
        
        # packet ID (answer with same ID as by the request)
        # FIXME
        # FIXME check how this works with data and 2x text from EX values???
        # FIXME
        int_ID = int(str(packet_ID), 16)
        bin_ID = '{:02x}'.format(int_ID)
        self.exbus_packet.extend(bin_ID)
        
        # telemetry identifier
        self.exbus_packet.extend(b'3A')

        # packet length in bytes of EX packet
        ex_packet_length = len(ex_packet)
        self.exbus_packet.extend('{:02x}'.format(ex_packet_length))

        # add EX packet
        self.exbus_packet.extend(ex_packet)

        # calculate the crc for the packet
        crc = CRC16.crc16_ccitt(self.exbus_packet)

        # compile final telemetry packet
        self.exbus_packet.extend(crc[2:4])
        self.exbus_packet.extend(crc[0:2])

        # print('Ex Bus Packet (ExBus.py)', self.ex.bytes2hex(self.exbus_packet))
        # print('Ex Bus Packet (ExBus.py)', self.exbus_packet)

        return self.exbus_packet

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

        self.i2c_sensors = i2c_sensors

        self.ex.Sensors(self.i2c_sensors)

        # cycle through sensors
        self.next_sensor = self.round_robin(i2c_sensors.available_sensors.keys())

        # cycle through data and text message
        self.next_message = self.round_robin(['data', 'text'])

    def round_robin(self, cycled_list):
        '''Light weight implementation for cycling periodically through sensors
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
            self.exbus = self.serial.read(8)
            self.checkTelemetryRequest()
        
        # EX bus CRC starts with first byte of the packet
        offset = 0
        
        # packet to check is message without last 2 bytes
        packet = bytearray(self.telemetryRequest[:-2])

        # the last 2 bytes of the message makeup the crc value for the packet
        packet_crc = self.telemetryRequest[-2:]

        # calculate the crc16-ccitt value of the packet
        crc = CRC16.crc16_ccitt(packet)

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

    def checkCRC(self, packet, crc_check):
        '''Do a CRC check using CRC16-CCITT

        Args:
            packet (bytearray): packet of Jeti Ex Bus including the checksum
                                The last two bytes of the packet are LSB and
                                MSB of the checksum. 

        Returns:
            bool: True if the crc check is OK, False if NOT
        '''
        crc = CRC16.crc16_ccitt(packet)

        return crc == crc_check
