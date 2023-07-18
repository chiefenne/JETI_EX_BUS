'''Python Implementation of the JETI EX Bus protocol

JETI Ex Bus specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/   
    File: EX_Bus_protokol_v121_EN.pdf


Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers

from ubinascii import hexlify, unhexlify
import utime
import micropython
from micropython import const

from Jeti import CRC16
from Utils.Logger import Logger


class ExBus:
    '''Jeti EX-BUS protocol handler.
    '''

    def __init__(self, serial, sensors, ex, lock):
        self.serial = serial
        self.sensors = sensors
        self.ex = ex
        self.old_packetID = b'\x00' # dummy value for initialization
        self.frame_count = 0
        
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

        # define states of the EX bus protocol
        #
        # header 1 is expected
        STATE_HEADER_1 = const(0)
        # header 2 is expected
        STATE_HEADER_2 = const(1)
        # length of the packet
        STATE_LENGTH = const(2)
        # packet end
        STATE_END = const(3)

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
                    buffer = bytearray()

                    # add the first byte to the buffer
                    buffer += bytearray(c)
                    
                    # change state
                    state = STATE_HEADER_2

            elif state == STATE_HEADER_2:
                # check for EX bus header 2
                if c in [b'\x01', b'\x03']:
                
                    buffer += bytearray(c)

                    # change state
                    state = STATE_LENGTH
                
                # else:
                #     # reset state
                #     state = STATE_HEADER_1

            elif state == STATE_LENGTH:
                # check for EX bus packet length
                buffer += bytearray(c)

                # packet length (including header and CRC)
                packet_length = buffer[2]
                # print('Packet length', packet_length)

                # check if packet length is valid
                # 6 bytes header + max. 24*2 bytes data + 2 bytes CRC
                # FIXME:
                # FIXME: check if above is correct (check also in STATE_END)
                # FIXME:
                if packet_length > 64:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # change state
                state = STATE_END

            elif state == STATE_END:

                if len(buffer) > 64:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # check for rest of EX bus packet
                # ID, data identifier, data, CRC
                buffer += bytearray(c)
                
                # check if packet is complete
                if len(buffer) == packet_length:
                    
                    # print('buffer', buffer)
                    
                    # check CRC
                    if self.checkCRC(buffer):
                        # packet is complete and CRC is correct
                        # print('Packet complete and CRC correct')
    
                        # NOTE: accessing the bytearray needs slicing in order
                        #       to return a byte and not an integer
                        #       buffer[0] returns an integer
                        #       buffer[0:1] returns a byte
                        #       this way no conversion is needed

                        # check for channel data
                        if buffer[0:1] == b'\x3e' and \
                           buffer[4:5] == b'\x31':
                            # get the channel data
                            self.getChannelData(buffer)

                        # check for telemetry request
                        elif buffer[0:1] == b'\x3d' and \
                             buffer[1:2] == b'\x01' and \
                             buffer[4:5] == b'\x3a':
                            
                            packetID = buffer[3:4]

                            # send telemetry data
                            self.sendTelemetry(packetID)

                        # check for JetiBox request
                        elif buffer[0:1] == b'\x3d' and \
                             buffer[1:2] == b'\x01' and \
                             buffer[4:5] == b'\x3b':
                            # send JetiBox menu data
                            self.sendJetiBoxMenu()

                    # reset state
                    state = STATE_HEADER_1
                    continue

    def getChannelData(self, buffer, verbose=False):
        self.channel = dict()
        
        num_channels = int.from_bytes(buffer[5:6], 'little') // 2

        if verbose:
            self.logger.log('info', 'Number of channels: ' + str(num_channels))

        for i in range(num_channels):
            self.channel[i] = buffer[6 + i*2 : 7 + i*2] + \
                              buffer[7 + i*2 : 8 + i*2]
            
            if verbose:
                self.logger.log('info',
                    'Channel: ' + str(i+1) + 
                    ' Value: ' + str(int.from_bytes(self.channel[i], 'little') / 8000)
                               + ' ms')
    
    def sendTelemetry(self, packetID, verbose=False):
        '''Send telemetry data back to the receiver (master).

        The packet ID is required to answer the request with the same ID.
        '''

        start = utime.ticks_us()

        # frame counter
        if packetID == self.old_packetID:
            self.frame_count += 1
        else:
            self.frame_count = 0

        # acquire lock to access the "ex" object" exclusively
        # core 1 cannot acquire the lock if core 0 has it
        self.lock.acquire()

        # EX BUS packet (send data and text alternately)
        # check if packet is available (set in main.py)
        if self.ex.exbus_device_ready:
        
            # description of the device
            telemetry = self.ex.exbus_device
            self.ex.exbus_device_ready = False

        elif self.ex.exbus_text1_ready and \
            self.frame_count <= 6:
        
            # description and unit for first telemetry value
            telemetry = self.ex.exbus_text1
            self.ex.exbus_text1_ready = False

        elif self.ex.exbus_text2_ready and \
            self.frame_count <= 6:

            # description and unit for second telemetry value
            telemetry = self.ex.exbus_text2
            self.ex.exbus_text2_ready = False

        elif self.ex.exbus_data_ready:

            # send two telemetry values
            telemetry = self.ex.exbus_data
            self.ex.exbus_data_ready = False
        else:
            if self.lock.locked():
                self.lock.release()
            return 0 # no data available

        if self.lock.locked():
            self.lock.release()


        # packet ID (answer with same ID as by the request)
        # slice assignment is required to write a byte to the bytearray
        # it does an implicit conversion from byte to integer
        telemetry[3:4] = packetID

        # calculate the crc for the packet (as the packet is complete now)
        # checksum for EX BUS starts at the 1st byte of the packet
        
        # use viper emitter code for crc calculation
        crc16_int = self.crc16_viper(telemetry, len(telemetry))

        # convert crc to bytes with little endian
        telemetry += crc16_int.to_bytes(2, 'little')

        # write packet to the EX bus stream
        bytes_written = self.serial.write(telemetry)

        end = utime.ticks_us()

        # print how long it took to send the packet       
        diff = utime.ticks_diff(end, start)

        # self.logger.log('debug', 'Packet ID: {}'.format(packetID))
        # self.logger.log('debug', 'Bytes written: {}'.format(bytes_written))
        # self.logger.log('debug', 'Time for answer: {} ms'.format(diff / 1000.))
        # self.logger.log('debug', 'Frame counter: {}'.format(self.frame_count))
        # self.logger.log('debug', 'CRC16 check: {}'.format(self.checkCRC(telemetry)))
        # if not self.checkCRC(telemetry):
        #     self.logger.log('debug', 'CRC16 WRONG, telemetry: {}'.format(telemetry))

        # save packet ID for next packet (to check if it is a new packet)
        self.old_packetID = packetID

        return bytes_written

    def sendJetiBoxMenu(self):
        pass

    @micropython.viper
    def crc16_viper(self, frame:ptr8, length:int) -> int:
        '''CRC calculation with micropython viper code emitter. This is
        faster than the normal python code but slower than the assembler'''
        crc16_int = 0
        for i in range(length):
            crc16_int ^= frame[i]
            for _ in range(8):
                if crc16_int & 1:
                    crc16_int = (crc16_int >> 1) ^ 0x8408
                else:
                    crc16_int >>= 1
        return crc16_int

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
        crc_int = CRC16.crc16_ccitt(packet[:-2], len(packet[:-2]))
        crc = hex(crc_int)[2:]

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
