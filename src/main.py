'''Python Implementation of the JETI EX Bus protocol

This module holds the overall program logic. It initializes the serial connection
between board and Jeti receiver.

Furter it connects via I2C to the sensors which are attached to the board.

After that it starts an endless loop to handle all data streams between the devices.



Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
import uos as os

from Jeti.Serial_UART import Serial
from Jeti.ExBus import ExBus
from Sensors.Sensor import Sensors
from Utils.Logger import Logger


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')

# print some information about the board
logger.log('info', 'Board: {}'.format(os.uname().machine))
logger.log('info', 'MicroPython version: {}'.format(sys.version))
logger.log('info', 'MicroPython build: {}'.format(sys.implementation.name))

# Serial connection bewtween Jeti receiver and microcontroller
# baudrate=125000, 8-N-1
serial = Serial()
serial.connect()

# collect sensors attached to the microcontroller via I2C
sensors = Sensors()

# run JETI Ex Bus
exbus = ExBus(serial, sensors)
exbus.run_forever()
