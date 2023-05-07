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
     3   |    1   |      LEN     |  Message length incl. header and CRC
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
   There is only little difference to the telemetry request:

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

from Jeti import CRC16
from Utils.Logger import Logger
from Utils.Streamrecorder import saveStream
from Jeti.Ex import Ex


class ExBus:
    '''JETI Ex Bus protocol handler
    Allows to connect to sensors via serial cpmmunication (UART)

    JETI uses 125kbaud or 250kbaud. The speed is prescribed by the
    receiver (master).
    The speed may be checked via the CRC check (see checkSpeed).
    '''

    def __init__(self, baudrate=125000, bits=8, parity=None, stop=1, port=3):
        self.serial = None
        self.exbusBuffer = bytearray()

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
        self.logger = Logger()

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

        # define states of the EX bus protocol
        #
        # header 1 is expected
        STATE_HEADER_1 = 0
        # header 2 is expected
        STATE_HEADER_2 = 1
        # length of the packet
        STATE_LENGTH = 2
        # packet end
        STATE_END = 3

        # current state
        state = STATE_HEADER_1

        # wait until the serial stream is available
        while not self.serial.any():
            utime.sleep_ms(1)

        while True:

            # read one byte from the serial stream (c is then of type bytes)
            c = self.serial.read(1)
            if c == None:
                continue
            cx = hexlify(bytes(c)).decode()
            print('c: ', c)
            print('cx: ', cx)
            print('type(c): ', type(c))

            if state == STATE_HEADER_1:

                # check for EX bus header 1
                if cx in ['3e', '3d']:
                    self.exbusBuffer = list()
                    print('cx in STATE_HEADER_1: ', cx)
                    self.exbusBuffer.extend(cx)
                    
                    # change state
                    state = STATE_HEADER_2

            elif state == STATE_HEADER_2:
                # check for EX bus header 2
                if cx in ['01', '03']:
                    print('cx in STATE_HEADER_2: ', cx)
                    self.exbusBuffer.extend(cx)

                    # check if telemetry or Jetibox request to allow answer
                    if self.exbusBuffer[0:4] == unhexlify('3d01'):
                        self.bus_allows_answer = True
                    else:
                        self.bus_allows_answer = False

                    # change state
                    state = STATE_LENGTH
                
                else:
                    # reset state
                    state = STATE_HEADER_1

            elif state == STATE_LENGTH:
                # check for EX bus packet length
                print('cx in STATE_LENGTH: ', cx)
                print('type(cx) in STATE_LENGTH: ', type(cx))
                self.exbusBuffer.extend(cx)

                print('len(self.exbusBuffer): ', len(self.exbusBuffer))
                print('self.exbusBuffer[0]: ', self.exbusBuffer[0])
                print('self.exbusBuffer[1]: ', self.exbusBuffer[1])
                print('self.exbusBuffer[2]: ', self.exbusBuffer[2])
                print('type(self.exbusBuffer[2])', type(self.exbusBuffer[2]))

                # packet length (including header and CRC)
                self.packet_length = int(hexlify(self.exbusBuffer[2]), 16)

                # check if packet length is valid
                # 6 bytes header + max. 24*2 bytes data + 2 bytes CRC
                # FIXME:
                # FIXME: check if this is correct
                # FIXME:
                if self.packet_length > 56:
                    # reset state
                    state = STATE_HEADER_1

                # change state
                state = STATE_END

            elif state == STATE_END:
                # check for rest of EX bus packet
                # ID, data identifier, data, CRC
                print('cx in STATE_END: ', cx)
                self.exbusBuffer.extend(cx)

                # check if packet is complete
                if len(self.exbusBuffer) == self.packet_length:
                    # check CRC
                    if self.checkCRC(self.exbusBuffer):
                        # packet is complete and CRC is correct
                        
                        # check for channel data
                        if self.exbusBuffer[0] == unhexlify('3e') and \
                           self.exbusBuffer[4] == unhexlify('31'):
                            # get the channel data
                            self.getChannelData()

                        # check for telemetry request
                        elif self.exbusBuffer[0] == unhexlify('3d') and \
                             self.exbusBuffer[4] == unhexlify('3a'):
                            # send telemetry data
                            packet_id = self.exbusBuffer[3]
                            self.sendTelemetry(packet_id)

                        # check for JetiBox request
                        elif self.exbusBuffer[0] == unhexlify('3d') and \
                             self.exbusBuffer[4] == unhexlify('3b'):
                            # send JetiBox menu data
                            self.sendJetiBoxMenu()

                    # reset state
                    state = STATE_HEADER_1

    def getChannelData(self):
        self.channel = dict()
        num_channels = self.exbusBuffer[5] / 2
        for i in range(num_channels):
            self.channel[i] = self.exbusBuffer[7 + i * 2] + \
                              self.exbusBuffer[6 + i * 2]
            self.logger.log('Channel: ' + str(i) + ' Value: ' + str(self.channel[i]))
    
    def sendTelemetry(self, packet_ID):
        '''Send telemetry data back to the receiver (master). Each call of this function
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
        # start = utime.ticks_us()
        bytes_written = self.serial.write(exbus_packet)
        # end = utime.ticks_us()
        # diff = utime.ticks_diff(end, start)
        #print('Time for answer:', diff / 1000., 'ms')

        # failed to write to serial stream
        if bytes_written is None:
            print('NOTHING WAS WRITTEN')

    def sendJetiBoxMenu(self):
        pass

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

        # FIXME:
        # FIXME: self.getChannelData() or similar needs to be implemented
        # FIXME: in order to get a channel data packet
        # FIXME:

        # get channel data packet to check if CRC is ok
        packet = self.getChannelData()[:-2]

        # the last 2 bytes of the message makeup the crc value for the packet
        packet_crc = self.getChannelData[-2:]

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

    def checkCRC(self, packet):
        '''Do a CRC check using CRC16-CCITT

        Args:
            packet (bytearray): packet of Jeti Ex Bus including the checksum
                                The last two bytes of the packet are LSB and
                                MSB of the checksum. 

        Returns:
            bool: True if the crc check is OK, False if NOT
        '''

        # packet to check is message without last 2 bytes
        crc = CRC16.crc16_ccitt(packet[:-2])

        # swap bytes in 2 byte crc value (LSB and MSB)
        crc = crc[2:4] + crc[0:2]

        # the last 2 bytes of the message makeup the crc value for the packet
        crc_check = packet[-2:]

        return crc == crc_check

    def debug(self):
        # write 1 second of the serial stream to a text file on the SD card
        # works for the Pyboard
        saveStream(self.serial, self.logger, duration=1000)

        return
