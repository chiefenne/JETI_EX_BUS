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
import _thread
from machine import Pin

from Jeti.Serial_UART import Serial
from Jeti.ExBus import ExBus
from Jeti.Ex import Ex
from Sensors.Sensors import Sensors
from Sensors.I2C import I2C_bus
from Utils.Logger import Logger
from Utils.Streamrecorder import saveStream
from Utils.round_robin import cycler


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')

# Serial connection bewtween Jeti receiver and microcontroller
# defaults: baudrate=125000, 8-N-1
s = Serial(port=0)
serial = s.connect()

# write 1 second of the serial stream to a text file for debugging purposes
DEBUG = False
if DEBUG:
    saveStream(serial, logger, filename='EX_Bus_stream.txt', duration=1000)

# setup the I2C bus (pins are board specific)
#    TINY2040 board: GPIO6, GPIO7 at port 1 (id=1)
i2c = I2C_bus(1, scl=Pin(7), sda=Pin(6), freq=400000)
addresses = i2c.scan()

# check for sensors attached to the microcontroller
sensors = Sensors(addresses, i2c.i2c)

# setup the JETI EX protocol
ex = Ex(sensors.get_sensors())

# setup the JETI EX BUS protocol
exbus = ExBus(serial, sensors, ex)

# function which is run on core 0
def core0():

    while True:

        # debug
        # exbus.dummy()

        exbus.run_forever()

# function which is run on core 1
def core1():

    # make a generator out of the list of sensors
    cycle_sensors = cycler(sensors.get_sensors())
    
    while True:

        # cycle infinitely through all sensors
        sensor = next(cycle_sensors)

        # collect data from currently selected sensor
        sensor.read()

        # debug
        # ex.dummy()

        # compile data into a JETI EX frame
        frame = ex.packet(sensor)
        # print('EX Frame: {}'.format(frame))

# start the second thread on core 1
logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())

# run the main loop on core 0
logger.log('info', 'Starting main loop on core 0')
core0()
