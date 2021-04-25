'''

Author: Dipl.-Ing. A. Ennemoser
Date: 14-04-2021
Version: 0.3

Changes:
    Version 0.2 - 14-04-2021: basic structure of the code established
    Version 0.1 - 14-04-2021: initial version of the implementation

'''

# modules with "u" in front are 
import usys as sys
import uos as os


# check if we are on a Pyboard (main development platform for this code)
if 'pyboard' in sys.platform:
    import pyb
    pyboard = True

import JetiExBus
import JetiSensor
import Logger


# setup a logger for the REPL
logger = Logger.Logger()

# write something to the REPL
logger.setPreString('MIRCOCONTROLLER')
message = 'Running main.py from {}.'.format(os.getcwd())
logger.log('info', message)
logger.resetPreString()

# switch on blue led to show we are active (only for pyboard)
if pyboard:
    blue = pyb.LED(4)
    blue.on()

# instantiate a Jeti ex bus connection (using default parameters)
# baudrate=125000, 8-N-1
exbus = JetiExBus.JetiExBus()

# write information and debug messages (only for pyboard REPL)
if pyboard:
    message = 'EX Bus to run on {} at port {}'.format(sys.platform,
                                                       exbus.port)
    logger.log('info', message)
    message = 'Parameters for serial connection at port {}: {}-{}-{}-{}'.format(exbus.port,
                exbus.baudrate, exbus.bits, exbus.parity, exbus.stop)
    logger.log('info', message)

    # os.uname is a named tuple
    # extract values per defined tuple name
    uname = os.uname()
    logger.log('info', 'System name: ' + uname.sysname)
    logger.log('info', 'Network name: ' + uname.nodename)
    logger.log('info', 'Version of underlying system: ' + uname.release)
    logger.log('info', 'MicroPython version: ' + uname.version)
    logger.log('info', 'Hardware identifier: ' + uname.machine)

# establish the serial connection
exbus.connect()

if pyboard:
    message = 'Serial connection established'
    logger.log('info', message)

# check (and if needed set) the connection speed (125000 or 250000)
exbus.checkSpeed()

# collect sensors attached via I2C
i2c = JetiSensor.I2C_Sensors()

# print sensor meta data at REPL
if pyboard:
    for sensor in i2c.available_sensors:
        message = 'Sensor {} of type {} available at address {}'.format(sensor,
            i2c.available_sensors[sensor]['type'],
            i2c.available_sensors[sensor]['address'])
        logger.log('info', message)

# transfer sensor meta data
exbus.Sensors(i2c.available_sensors)

# run JETI Ex Bus
exbus.run_forever()
