'''Python Implementation of the JETI EX Bus protocol


Implementation via MicroPython (Python for microprocessors):
    https://micropython.org/
    https://github.com/micropython/micropython    


JETI Ex Bus specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/
    
'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from machine import UART
import uasyncio as asyncio

import CRC16
import Logger


class JetiExBus:
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

        self.telemetry = bytearray()
        self.get_new_sensor = False

        # setup a logger for the REPL
        self.logger = Logger.Logger()

        # connect to the serial stream of the Jeti receiver
        self.connect()

        asyncio.create_task(self.run_forever())

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

    def __iter__(self):
        '''This method is called exactly once.
        See sensor classes.
        '''
        while self.value is None:
            yield from asyncio.sleep_ms(0)

    async def run_forever(self):
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
            await asyncio.sleep_ms(0)
    
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
        bytes_written = self.serial.write(exbus_packet)

        # failed to write to serial stream
        if bytes_written is None:
            print('NOTHING WAS WRITTEN')

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

        self.jetiex.Sensors(self.i2c_sensors)

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
