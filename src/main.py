'''JETI EX Bus protocol. Implemented using MicroPython.

For sensor telemetry data transmission between a microcontroller and a
JETI receiver.

Source code and documentation:
    https://github.com/chiefenne/JETI_EX_BUS

JETI Ex Bus and JETI Ex protocol specification:
    http://www.jetimodel.com/en/Telemetry-Protocol/
    EX_Bus_protokol_v121_EN.pdf
    JETI_Telem_protocol_EN_V1.07.pdf


This module holds the overall program logic. It initializes the serial connection
between microcontroller (board) and Jeti receiver.
Further it connects the sensors via I2C to the board.
After that it starts an endless loop to handle all data streams between the devices.
The code runs on two cores of the microcontroller.


Author: Dipl.-Ing. A. Ennemoser
Date: 01-2025

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
from machine import Pin
import _thread

from Jeti.Ex import Ex
from Jeti.ExBus import ExBus

from Jeti.Serial_UART import Serial
from Sensors.I2C import I2C_bus
from Sensors.Sensors import Sensors
from Utils.Logger import Logger
from Utils.Streamrecorder import saveStream


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')

# lock object used to prevent other cores from accessing shared resources
lock = _thread.allocate_lock()

# Serial connection bewtween Jeti receiver and microcontroller
# defaults: baudrate=125000, 8-N-1
# Default to port 0 (e.g., for RP2040-based boards)
port = 0

# Override for other platforms if needed, for example ESP32
if 'esp32' in sys.platform:
    port = 1

# log message to inform the user about the serial port
logger.log('info', 'Connecting serial on port: {}'.format(port))

s = Serial(port=port, baudrate=125000, bits=8, parity=None, stop=1)
serial = s.connect()

# write 3 seconds of the serial stream to a text file for debugging purposes
DEBUG = False
if DEBUG:
    logger.log('debug', 'Starting to record EX Bus stream ...')
    saveStream(serial, filename='EX_Bus_stream.txt', duration=3000)
    logger.log('debug', 'EX Bus stream recorded')

# setup the I2C bus (pins are board specific)
#    TINY2040 board: GPIO6, GPIO7 at port 1 (id=1)
#    ESP32 board: GPIO5, GPIO6 at port ??
if 'rp2' in sys.platform:
    i2c = I2C_bus(1, scl=Pin(7), sda=Pin(6), freq=400000)
if 'esp32' in sys.platform:
    i2c = I2C_bus(1, scl=Pin(6), sda=Pin(5), freq=400000)

# scan the I2C bus for sensors
addresses = i2c.scan()

# check for sensors attached to the microcontroller
sensors = Sensors(addresses, i2c.i2c)

# setup the JETI EX protocol
ex = Ex(sensors, lock)

# setup the JETI EX BUS protocol
exbus = ExBus(serial, sensors, ex, lock)

def core0():
    run_with_interrupt_handling(exbus, 'core 0')

def core1():
    run_with_interrupt_handling(ex, 'core 1')

def run_with_interrupt_handling(target, core_name):
    try:
        target.run_forever()
    except KeyboardInterrupt:
        logger.log('info', f'Keyboard interrupt on {core_name}')
        logger.log('info', 'Exit program')

# start the second thread on core 1
logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())

# run the main loop on core 0
logger.log('info', 'Starting main loop on core 0')
core0()
