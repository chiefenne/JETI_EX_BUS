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


# check if we are on a Pyboard (main development platform for this code)
pyboard = False
if 'pyboard' in sys.platform:
    import pyb
    pyboard = True

from Jeti.Protocols.ExBus import ExBus
import Jeti.JetiSensor as JetiSensor
import Logger


# setup a logger for the REPL
logger = Logger.Logger()

# switch on blue led to show we are active (only for pyboard)
if pyboard:
    blue = pyb.LED(4)
    blue.on()

# instantiate a Jeti ex bus connection (using default parameters)
# baudrate=125000, 8-N-1
exbus = ExBus()

# write information and debug messages (only for pyboard REPL)
if pyboard:
    message = 'EX Bus to run on {} at port {}'.format(sys.platform,
                                                       exbus.port)
    logger.log('info', message)
    message = 'Parameters for serial connection at port {}: {}-{}-{}-{}'.format(exbus.port,
                exbus.baudrate, exbus.bits, exbus.parity, exbus.stop)
    logger.log('info', message)

# establish the serial connection
exbus.connect()

if pyboard:
    message = 'Serial connection established'
    logger.log('info', message)

# check (and if needed set) the connection speed (125000 or 250000)
# exbus.checkSpeed()

# collect sensors attached via I2C
i2c_sensors = JetiSensor.I2C_Sensors()

# transfer sensor meta data
exbus.Sensors(i2c_sensors)

# run JETI Ex Bus
exbus.run_forever()
