'''
Establishes a serial connection to the Jeti Transmitter via UART.
Jeti ex bus protocol runs 8-N-1, speed any of 125000 or 250000 baud.
Currently (2023) only 125000 baud is supported.


Author: Dipl.-Ing. A. Ennemoser
Date: 05-2023

'''
from machine import UART
from Utils.Logger import Logger

class Serial:

    def __init__(self, port=0,
                       baudrate=115200,
                       bits=8,
                       parity=None,
                       stop=1,
                       timeout=1000):
        '''Constructor of Serial class.
        '''
        self.port = port
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.timeout = timeout

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SERIAL')

        self.uart = UART(port, baudrate, bits, parity, stop, timeout)
    
    def connect(self):
        '''Establish a serial connection.
        '''
        self.uart.init(self.baudrate, self.bits, self.parity, self.stop, self.timeout)
        self.logger.log('info', 'Serial connection established')

    def disconnect(self):
        '''Close the serial connection.
        '''
        self.uart.deinit()
        self.logger.log('info', 'Serial connection closed')


