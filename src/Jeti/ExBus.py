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

    def __init__(self, serial, sensors):
        self.serial = serial
        self.sensors = sensors

        # instantiate the EX protocol
        self.ex = Ex()

        self.exbusBuffer = bytearray()
        self.telemetry = bytearray()
        self.get_new_sensor = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EXBUS')

    def run_forever(self):
        '''This is the main loop and will run forever. This function is called
        at the end of the function "main.py". It does exactly the same as the
        Arduino "loop()" function.

        Within the loop the datastream of the EX bus is checked for:
          1) Telemetry request (a sensor can send data)
          2) JetiBox request (modify parameters)
          3) Channel data (current status of the transmitter)
        '''

        # log the start of the main loop
        self.logger.log('info', 'Starting EX Bus main loop')

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

        # initial state
        state = STATE_HEADER_1

        # wait until the serial stream is available
        while not self.serial.any():
            utime.sleep_ms(10)
        
        while True:

            # read one byte from the serial stream
            c = self.serial.read(1)
            
            # check if something was read from the bus
            if c == None:
                continue

            if state == STATE_HEADER_1:

                # check for EX bus header 1
                if c in [b'\x3e',  b'\x3d']:

                    # initialize the buffer
                    self.exbusBuffer = bytearray()

                    # add the first byte to the buffer
                    self.exbusBuffer += bytearray(c)
                    
                    # change state
                    state = STATE_HEADER_2

            elif state == STATE_HEADER_2:
                # check for EX bus header 2
                if c in [b'\x01', b'\x03']:
                    self.exbusBuffer += bytearray(c)

                    # check if telemetry or Jetibox request to allow answer
                    if self.exbusBuffer[0] == 0x3d and \
                       self.exbusBuffer[1] == 0x01:
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
                self.exbusBuffer += bytearray(c)

                # packet length (including header and CRC)
                self.packet_length = self.exbusBuffer[2]
                # print('Packet length', self.packet_length)

                # check if packet length is valid
                # 6 bytes header + max. 24*2 bytes data + 2 bytes CRC
                # FIXME:
                # FIXME: check if above is correct
                # FIXME:
                if self.packet_length > 64:
                    # reset state
                    state = STATE_HEADER_1

                # change state
                state = STATE_END

            elif state == STATE_END:
                # check for rest of EX bus packet
                # ID, data identifier, data, CRC
                self.exbusBuffer += bytearray(c)

                # check if packet is complete
                if len(self.exbusBuffer) == self.packet_length:
                    
                    # print('self.exbusBuffer', self.exbusBuffer)
                    
                    # check CRC
                    if self.checkCRC(self.exbusBuffer):
                        # packet is complete and CRC is correct
    
                        # NOTE: accessing the bytearray needs slicing in order
                        #       to return a byte and not an integer
                        #       self.exbusBuffer[0] returns an integer
                        #       self.exbusBuffer[0:1] returns a byte
                        #       this way no conversion is needed

                        # check for channel data
                        if self.exbusBuffer[0:1] == b'\x3e' and \
                           self.exbusBuffer[4:5] == b'\x31':
                            # get the channel data
                            self.getChannelData()

                        # check for telemetry request
                        elif self.exbusBuffer[0:1] == b'\x3d' and \
                             self.exbusBuffer[4:5] == b'\x3a':
                            
                            packet_id = self.exbusBuffer[3:4]
                            print('Telemetry packet ID', packet_id)

                            # send telemetry data
                            self.sendTelemetry(packet_id)

                        # check for JetiBox request
                        elif self.exbusBuffer[0:1] == b'\x3d' and \
                             self.exbusBuffer[4:5] == b'\x3b':
                            print('Need to send JETIBOX')
                            # send JetiBox menu data
                            # self.sendJetiBoxMenu()

                    # reset state
                    state = STATE_HEADER_1

    def getChannelData(self):
        self.channel = dict()
        
        num_channels = int.from_bytes(self.exbusBuffer[5:6], 'little') // 2
        self.logger.log('info', 'Number of channels: ' + str(num_channels))

        for i in range(num_channels):
            self.channel[i] = self.exbusBuffer[6 + i*2 : 7 + i*2] + \
                              self.exbusBuffer[7 + i*2 : 8 + i*2]
            self.logger.log('info',
                'Channel: ' + str(i+1) + 
                ' Value: ' + str(int.from_bytes(self.channel[i], 'little') / 8000)
                           + ' ms')
    
    def sendTelemetry(self, packet_ID):
        '''Send telemetry data back to the receiver (master). Each call of this function
        sends data from the next sensor or data type in the queue.
        '''

        # compile the complete EX bus packet
        exbus_packet = self.ExBusPacket(packet_ID)

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

        # check if there is a sensor in the queue
        if len(self.sensor_queue) > 0:
            # get the next sensor from the queue
            self.current_sensor = self.sensor_queue.pop(0)
            print('Current sensor:', self.current_sensor)
        
        # set EX type
        EX_type = 'data'
        
        # get the EX packet for the current sensor
        ex_packet = self.ex.ExPacket(self.current_sensor, EX_type)

        # EX bus header
        self.exbus_packet = b'\x3B\x01'

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

        return self.exbus_packet

    def round_robin(self, cycled_list):
        '''Light weight implementation for cycling periodically through sensors
        Source: https://stackoverflow.com/a/36657230/2264936
        
        Args:
            sensors (list): Any list which should be cycled
        Yields:
            Next element in the list

        Example usage:
            next_sensor = self.round_robin(i2c_sensors.available_sensors.keys())

        '''
        while cycled_list:
            for element in cycled_list:
                yield element

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

        # the last 2 bytes of the message makeup the crc value for the packet
        crc_check = hexlify(packet[-2:]).decode()

        # swap bytes in 2 byte crc value (LSB and MSB)
        crc = crc[2:4] + crc[0:2]
        
        # print('crc', crc)
        # print('crc_check', crc_check)
        
        if crc == crc_check:
            return True
        else:
            return False

    def debug(self):
        # write 1 second of the serial stream to a text file on the SD card
        # works for the Pyboard
        saveStream(self.serial, self.logger, duration=1000)

        return
