'''Python Implementation of the JETI EX Bus protocol

JETI Ex Bus specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/
    File: EX_Bus_protokol_v121_EN.pdf

Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers

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
        STATE_HEADER_1 = const(0)
        STATE_HEADER_2 = const(1)
        STATE_LENGTH = const(2)
        STATE_END = const(3)

        state = STATE_HEADER_1
        while True:
            # Read available bytes from the serial stream
            available_bytes = self.serial.any()
            if available_bytes > 0:
                c = self.serial.read(1)

                if state == STATE_HEADER_1:
                    if c in [b'\x3e', b'\x3d']:
                        buffer = bytearray(c)
                        state = STATE_HEADER_2

                elif state == STATE_HEADER_2:
                    if c in [b'\x01', b'\x03']:
                        buffer += c
                        state = STATE_LENGTH

                elif state == STATE_LENGTH:
                    buffer += c
                    packet_length = buffer[2]
                    if packet_length > 60:
                        state = STATE_HEADER_1
                        continue
                    state = STATE_END

                elif state == STATE_END:
                    if len(buffer) > 60:
                        state = STATE_HEADER_1
                        continue

                    buffer += c
                    if len(buffer) == packet_length:
                        if self.checkCRC(buffer):
                            if buffer[0:1] == b'\x3e' and buffer[4:5] == b'\x31':
                                self.getChannelData(buffer)
                            elif buffer[:2] == b'\x3d\x01' and buffer[4:5] == b'\x3a':
                                self.sendTelemetry(buffer[3:4])
                            elif buffer[:2] == b'\x3d\x01' and buffer[4:5] == b'\x3b':
                                self.sendJetiBoxMenu()
                        state = STATE_HEADER_1
                        continue

    @micropython.native
    def getChannelData(self, buffer):
        self.channel = {}
        num_channels = buffer[5] // 2  # Optimized access
        for i in range(num_channels):
            start_index = 6 + i * 2
            self.channel[i] = buffer[start_index:start_index + 2]

    @micropython.native
    def sendTelemetry(self, packetID):
        '''Send telemetry data back to the receiver (master).

        The packet ID is required to answer the request with the same ID.
        '''
        self.frame_count += 1

        # Optimization: Read ex properties once before the lock
        exbus_device_ready = self.ex.exbus_device_ready
        exbus_data_ready = self.ex.exbus_data_ready
        n_labels = self.ex.n_labels

        with self.lock:
            if exbus_device_ready and self.frame_count <= self.label_frames:
                telemetry = self.ex.dev_labels_units[self.frame_count % n_labels]
            elif exbus_data_ready and self.frame_count > self.label_frames:
                telemetry = self.ex.exbus_data
                self.ex.exbus_data_ready = False
            else:
                return 0

        # Optimization: Construct packet ID once
        telemetry_ID = telemetry[:3] + packetID + telemetry[4:]

        # Optimization: Calculate CRC and append
        crc16_int = CRC16.crc16_ccitt(telemetry_ID, len(telemetry_ID))
        telemetry_ID_CRC16 = telemetry_ID + crc16_int.to_bytes(2, 'little')

        # Optimization: Write to serial once
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
        crc_calculated = CRC16.crc16_ccitt(packet[:-2], len(packet[:-2]))
        crc_received = int.from_bytes(packet[-2:], 'little')  # Optimized CRC extraction
        return crc_calculated == crc_received