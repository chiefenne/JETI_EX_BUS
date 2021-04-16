'''

Author: Dipl.-Ing. A. Ennemoser
Date: 14-04-2021
Version: 0.2

Changes:
    Version 0.2 - 14-04-2021: update for RP2040 based boards
    Version 0.1 - 14-04-2021: initial version of the implementation

'''


import usys
import uos
import utime
import ubinascii

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
    red = pyb.LED(1)
    green = pyb.LED(2)
    orange = pyb.LED(3)
    blue = pyb.LED(4)

    # led working indicator for Pyboard
    blue.on()

# instantiate a Jeti ex bus connection
exbus = JetiExBus.JetiExBus()

# write information and debug messages (visible on the REPL)
exbus.info()

# establish the serial connection
exbus.connect()

# check (and if needed set) the correct connection speed 
# one of 125000 or 250000
# exbus.checkSpeed(packet)

# run JETI Ex Bus
exbus.run_forever()
