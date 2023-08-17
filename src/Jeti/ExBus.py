'''Python Implementation of the JETI EX Bus protocol

JETI Ex Bus specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/   
    File: EX_Bus_protokol_v121_EN.pdf


Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers

from ubinascii import hexlify
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
        self.frame_count = -1

        # number of frames for sending initial device and label information
        self.label_frames = 100

        
        # lock object used to prevent other cores from accessing shared resources
        self.lock = lock

        self.get_new_sensor = False

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI EXBUS')

    @micropython.native
    def run_forever(self):
        '''This is the main loop and will run forever.

        Within the loop the datastream of the EX bus is checked for:
          - Channel data (current status of the transmitter controls)
          - Telemetry request (a sensor can send data)
          - JetiBox request (modify parameters)

        NOTE: bytearrays needs slicing in order to return a byte and not an integer
              buffer[0] returns an integer
              buffer[0:1] returns a byte

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
                    buffer = bytearray()
                    buffer += bytearray(c)
                    
                    # change state
                    state = STATE_HEADER_2

            elif state == STATE_HEADER_2:
                # check for EX bus header 2
                if c in [b'\x01', b'\x03']:
                    buffer += bytearray(c)

                    # change state
                    state = STATE_LENGTH
                
            elif state == STATE_LENGTH:
                # check for EX bus packet length
                buffer += bytearray(c)

                # packet length (including header and CRC)
                packet_length = buffer[2]

                # check if packet length is valid
                # 6 bytes header + max. 24*2 bytes data + 2 bytes CRC
                if packet_length > 60:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # change state
                state = STATE_END

            elif state == STATE_END:

                if len(buffer) > 60:
                    # reset state
                    state = STATE_HEADER_1
                    continue

                # update rest of EX bus packet (ID, data identifier, data, CRC)
                buffer += bytearray(c)
                
                # check if packet is complete
                if len(buffer) == packet_length:
                    
                    # check CRC
                    if self.checkCRC(buffer): # packet is complete and CRC is correct
    
                        # check for channel data
                        if buffer[0:1] == b'\x3e' and \
                           buffer[4:5] == b'\x31':
                            self.getChannelData(buffer)

                        # check for telemetry request
                        elif buffer[:2] == b'\x3d\x01' and buffer[4:5] == b'\x3a':
                            self.sendTelemetry(buffer[3:4])

                        # check for JetiBox request
                        elif buffer[:2] == b'\x3d\x01' and buffer[4:5] == b'\x3b':
                            self.sendJetiBoxMenu()

                    # reset state
                    state = STATE_HEADER_1
                    continue

    @micropython.native
    def getChannelData(self, buffer):
        self.channel = dict()
        
        num_channels = int.from_bytes(buffer[5:6], 'little') // 2

        for i in range(num_channels):
            self.channel[i] = buffer[6 + i*2 : 7 + i*2] + \
                              buffer[7 + i*2 : 8 + i*2]

    @micropython.native
    def sendTelemetry(self, packetID):
        '''Send telemetry data back to the receiver (master).

        The packet ID is required to answer the request with the same ID.
        '''

        # frame counter
        self.frame_count += 1

        # acquire lock to access the "ex" object" exclusively
        self.lock.acquire()

        if self.ex.exbus_device_ready and self.frame_count <= self.label_frames:
            # send device and label information (cycle through labels)
            telemetry = self.ex.dev_labels_units[self.frame_count % self.ex.n_labels]

        elif self.ex.exbus_data_ready and self.frame_count > self.label_frames:
            # send telemetry values
            telemetry = self.ex.exbus_data
            self.ex.exbus_data_ready = False

        else: # no data available
            if self.lock.locked():
                self.lock.release()
            return 0 

        if self.lock.locked():
            self.lock.release()

        # packet ID (answer with same ID as by the request)
        telemetry_ID = telemetry[:3] + packetID + telemetry[4:]

        # calculate the crc for the packet (as the packet is complete now)
        crc16_int = CRC16.crc16_ccitt(telemetry_ID, len(telemetry_ID))

        # convert crc to bytes with little endian
        telemetry_ID_CRC16 = telemetry_ID + crc16_int.to_bytes(2, 'little')

        # write packet to the EX bus stream
        bytes_written = self.serial.write(telemetry_ID_CRC16)

        return bytes_written

    def sendJetiBoxMenu(self):
        pass

    @micropython.native
    def checkCRC(self, packet):
        '''Do a CRC check using CRC16-CCITT

        Args:
            packet : packet of Jeti Ex Bus including the checksum
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
        
        if crc == crc_check:
            return True
        else:
            return False

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
        self.logger.log(
            'info', 'core 0: EX BUS lock released after {} us'.format(diff))
