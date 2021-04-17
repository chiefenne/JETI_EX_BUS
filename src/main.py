'''

Author: Dipl.-Ing. A. Ennemoser
Date: 14-04-2021
Version: 0.3

Changes:
    Version 0.2 - 14-04-2021: basic structure of the code established
    Version 0.1 - 14-04-2021: initial version of the implementation

'''

import usys
import uos
import utime
import ubinascii

# check if we are on a Pyboard (main development platform for this code)
if 'pyboard' in usys.platform:
    import pyb
    pyboard = True

import JetiExBus
import Logger


# setup a logger for the REPL
logger = Logger.Logger()

# write something to the REPL
logger.setPreString('MIRCOCONTROLLER')
message = 'Running main.py from {}.'.format(uos.getcwd())
logger.log('info', message)
logger.resetPreString()

# switch on blue led to show we are active (only for pyboard)
if pyboard:
    blue = pyb.LED(4)
    blue.on()

# instantiate a Jeti ex bus connection (using default parameters)
# baudrate=125000, 8-N-1
exbus = JetiExBus.JetiExBus()

# write information and debug messages (visible on the REPL)
exbus.info()

# establish the serial connection
exbus.connect()

message = 'Serial connection established'
logger.log('info', message)

# check (and if needed set) the correct connection speed 
# one of 125000 or 250000
# exbus.checkSpeed(packet)

# run JETI Ex Bus
exbus.run_forever()
