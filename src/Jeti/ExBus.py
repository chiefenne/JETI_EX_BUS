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
import ustruct

from Jeti import CRC16
from Utils.Logger import Logger


class ExBus:
    '''Jeti EX-BUS protocol handler.
    '''

    def __init__(self, serial, sensors, ex, lock):
        self.serial = serial
        self.sensors = sensors
        self.ex = ex
        self.toggle = False
        self.device_sent = False
        
        # lock object used to prevent other cores from accessing shared resources
        self.lock = lock

        self.get_new_sensor = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EXBUS')

    def dummy(self):
        '''Dummy function for checking lock.
        Stay 3 seconds in the lock.
        '''
        self.logger.log('info', 'core 0: EX BUS trying to acquire lock')
        start = utime.ticks_us()
        self.lock.acquire()
        utime.sleep_ms(3000)
        self.lock.release()
        end = utime.ticks_us()
        diff = utime.ticks_diff(end, start)
        self.logger.log('info', 'core 0: EX BUS lock released after {} us'.format(diff))

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

        # initialize the state
        state = STATE_HEADER_1

        while True:

            # read one byte from the serial stream
            if self.serial.any():
                c = self.serial.read(1)

            if state == STATE_HEADER_1:

                # check for EX bus header 1
                if c in [b'\x3e',  b'\x3d']:

                    # initialize the buffer
                    self.buffer = bytearray()

                    # add the first byte to the buffer
                    self.buffer += bytearray(c)
                    
                    # change state
                    state = STATE_HEADER_2

            elif state == STATE_HEADER_2:
                # check for EX bus header 2
                if c in [b'\x01', b'\x03']:
                
                    self.buffer += bytearray(c)

                    # change state
                    state = STATE_LENGTH
                
                # else:
                #     # reset state
                #     state = STATE_HEADER_1

            elif state == STATE_LENGTH:
                # check for EX bus packet length
                self.buffer += bytearray(c)

                # packet length (including header and CRC)
                self.packet_length = self.buffer[2]
                # print('Packet length', self.packet_length)

                # check if packet length is valid
                # 6 bytes header + max. 24*2 bytes data + 2 bytes CRC
                # FIXME:
                # FIXME: check if above is correct
                # FIXME:
                if self.packet_length > 64:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # change state
                state = STATE_END

            elif state == STATE_END:

                if len(self.buffer) > 64:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # check for rest of EX bus packet
                # ID, data identifier, data, CRC
                self.buffer += bytearray(c)
                
                # check if packet is complete
                if len(self.buffer) == self.packet_length:
                    
                    # print('self.buffer', self.buffer)
                    
                    # check CRC
                    if self.checkCRC(self.buffer):
                        # packet is complete and CRC is correct
                        # print('Packet complete and CRC correct')
    
                        # NOTE: accessing the bytearray needs slicing in order
                        #       to return a byte and not an integer
                        #       self.buffer[0] returns an integer
                        #       self.buffer[0:1] returns a byte
                        #       this way no conversion is needed

                        # check for channel data
                        if self.buffer[0:1] == b'\x3e' and \
                           self.buffer[4:5] == b'\x31':
                            # get the channel data
                            self.getChannelData()

                        # check for telemetry request
                        elif self.buffer[0:1] == b'\x3d' and \
                             self.buffer[1:2] == b'\x01' and \
                             self.buffer[4:5] == b'\x3a':
                            
                            packet_id = self.buffer[3:4]

                            # send telemetry data
                            self.sendTelemetry(packet_id, verbose=False)

                        # check for JetiBox request
                        elif self.buffer[0:1] == b'\x3d' and \
                             self.buffer[1:2] == b'\x01' and \
                             self.buffer[4:5] == b'\x3b':
                            # send JetiBox menu data
                            self.sendJetiBoxMenu()

                    # reset state
                    state = STATE_HEADER_1
                    continue

    def getChannelData(self, verbose=False):
        self.channel = dict()
        
        num_channels = int.from_bytes(self.buffer[5:6], 'little') // 2

        if verbose:
            self.logger.log('info', 'Number of channels: ' + str(num_channels))

        for i in range(num_channels):
            self.channel[i] = self.buffer[6 + i*2 : 7 + i*2] + \
                              self.buffer[7 + i*2 : 8 + i*2]
            
            if verbose:
                self.logger.log('info',
                    'Channel: ' + str(i+1) + 
                    ' Value: ' + str(int.from_bytes(self.channel[i], 'little') / 8000)
                               + ' ms')
    
    def sendTelemetry(self, packet_ID, verbose=False):
        '''Send telemetry data back to the receiver (master).

        The packet ID is required to answer the request with the same ID.
        '''

        start = utime.ticks_us()

        # acquire lock to access the "ex" object" exclusively
        # core 1 cannot acquire the lock if core 0 has it
        self.lock.acquire()

        # send device name once at the beginning
        if not self.device_sent and self.ex.exbus_device_ready:
            self.telemetry = self.ex.exbus_device
            self.device_sent = True
            self.lock.release()

            if verbose:
                self.logger.log('info', 'Packet ID of telemetry request: {}'.format(hexlify(packet_ID)))
                self.logger.log('info', 'Device name: {}'.format(self.ex.device))

        # EX BUS packet (send data and text alternately)
        if self.device_sent:

            # check if EX packet is available (set in main.py)
            if self.toggle and self.ex.exbus_text_ready:
                self.telemetry = self.ex.exbus_text
                self.ex.exbus_text_ready = False
            elif not self.toggle and self.ex.exbus_data_ready:
                self.telemetry = self.ex.exbus_data
                self.ex.exbus_data_ready = False

            self.toggle = not self.toggle
            self.lock.release()
        else:
            self.lock.release()
            return

        # packet ID (answer with same ID as by the request)
        # slice assignment is required to write a byte to the bytearray
        # it does an implicit conversion from byte to integer
        self.telemetry[3:4] = packet_ID

        # write packet to the EX bus stream
        bytes_written = self.serial.write(self.telemetry)

        if verbose:
            self.logger.log('info', 'Packet ID of telemetry request: {}'.format(hexlify(packet_ID)))
            self.logger.log('info', 'Telemetry data: {}'.format(hexlify(self.telemetry)))   
        
        # print how long it took to send the packet       
        end = utime.ticks_us()
        diff = utime.ticks_diff(end, start)
        print('Time for answer:', diff / 1000., 'ms')

        return bytes_written

    def sendJetiBoxMenu(self):
        pass

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
