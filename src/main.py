'''JETI EX Bus protocol. Implemented using MicroPython.

For sensor telemetry data transmission between a microcontroller and a
JETI receiver.

Source code and documentation:
    https://github.com/chiefenne/JETI_EX_BUS


JETI Ex Bus and JETI Ex specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/   
    EX_Bus_protokol_v121_EN.pdf
    JETI_Telem_protocol_EN_V1.07.pdf

MicroPython:
   https://micropython.org/
   https://github.com/micropython/micropython    


This module holds the overall program logic. It initializes the serial connection
between microcontroller (board) and Jeti receiver.

Further it connects the sensors via I2C to the board.

After that it starts an endless loop to handle all data streams between the devices.


Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
import uos as os
import machine
from machine import Pin
import _thread

from Jeti.Ex import Ex
from Jeti.ExBus import ExBus
from Jeti.Serial_UART import Serial
from Sensors.I2C import I2C_bus
from Sensors.Sensors import Sensors
from Utils.Logger import Logger
from Utils import status
from Utils.Streamrecorder import saveStream


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')

# overclock the microcontroller (default is 125 MHz)
# machine.freq(250000000)

# lock object used to prevent other cores from accessing shared resources
lock = _thread.allocate_lock()

# Serial connection bewtween Jeti receiver and microcontroller
# defaults: baudrate=125000, 8-N-1
s = Serial(port=0, baudrate=125000, bits=8, parity=None, stop=1)
serial = s.connect()

# write 3 seconds of the serial stream to a text file for debugging purposes
DEBUG = False
if DEBUG:
    logger.log('debug', 'Starting to record EX Bus stream ...')
    saveStream(serial, filename='EX_Bus_stream.txt', duration=3000)
    logger.log('debug', 'EX Bus stream recorded')

# setup the I2C bus (pins are board specific)
#    TINY2040 board: GPIO6, GPIO7 at port 1 (id=1)
i2c = I2C_bus(1, scl=Pin(7), sda=Pin(6), freq=400000)

# offer a demo sensor if no sensor is attached to the microcontroller
# works if a file named 'demo.txt' is present
demo = 'demo.txt' in os.listdir()

# scan the I2C bus for sensors
addresses = i2c.scan(demo=demo)

# check for sensors attached to the microcontroller
sensors = Sensors(addresses, i2c.i2c)

# setup the JETI EX protocol
ex = Ex(sensors, lock)

# setup the JETI EX BUS protocol
exbus = ExBus(serial, sensors, ex, lock)

# function which is run on core 0
def core0():

    # run the main loop on core 0
    exbus.run_forever()

# function which is run on core 1
def core1():

    # run the second thread on core 1
    ex.run_forever()

    # inform the user that the second thread is stopped
    logger.log('info', 'Stopping second thread on core 1')
 
# start the second thread on core 1
logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())    

try:
    # run the main loop on core 0
    logger.log('info', 'Starting main loop on core 0')
    core0()
except KeyboardInterrupt:
    status.main_thread_running = False
    logger.log('info', 'Keyboard interrupt occurred')
    logger.log('info', 'Stopping main thread on core 0')
    # stop the main thread
    _thread.exit()