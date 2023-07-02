'''
Establishes an UART (serial) connection to the Jeti Transmitter.
The Jeti ex bus protocol runs 8-N-1, speed any of 125000 or 250000 baud.
Currently (2023) only 125000 baud is supported.


Author: Dipl.-Ing. A. Ennemoser
Date: 05-2023

'''

import usys as sys

from machine import UART
from Utils.Logger import Logger


class Serial:

    def __init__(self, port=0,
                       baudrate=125000,
                       bits=8,
                       parity=None,
                       stop=1,
                       timeout=0):
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

    def connect(self):

        # instantiate UART connection
        self.uart = UART(self.port, 
                         baudrate=self.baudrate,
                         bits=self.bits,
                         parity=self.parity,
                         stop=self.stop,
                         timeout=self.timeout)
        
        # check if the connection was successful
        # self.check_connection()
    
        return self.uart
    
    def check_connection(self):
        
        if not self.uart.read():
            self.logger.log('error', 'Serial connection failed')
            self.logger.log('error', 'Connect a receiver to the UART port')
            sys.exit()
        else:
            self.logger.log('info', 'Serial connection established')
            self.logger.log('info', 'EX Bus protocol running at {}'.format(self.uart))
    
    def disconnect(self):
        '''Close the UART (serial) connection.

        This method is not used in the current implementation.

        '''
        self.uart.deinit()
        self.logger.log('info', 'Serial connection closed')

        return
