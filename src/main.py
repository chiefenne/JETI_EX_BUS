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

from Jeti.Serial_UART import Serial
from Jeti.ExBus import ExBus
from Jeti.Ex import Ex
from Sensors.Sensors import Sensors
from Utils.Logger import Logger
from Utils.Streamrecorder import saveStream
from Utils.round_robin import cycler


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')

# Serial connection bewtween Jeti receiver and microcontroller
# baudrate=125000, 8-N-1
serial = Serial()

# write 1 second of the serial stream to a text file for debugging purposes
DEBUG = False
if DEBUG:
    saveStream(serial, logger, filename='EX_Bus_stream.txt', duration=1000)

# collect sensors attached to the microcontroller via I2C
sensors = Sensors()

# setup the JETI EX protocol
ex = Ex()

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

    cycle_sensors = cycler(sensors.get_sensors())
    
    while True:

        # cycle infinitely through all sensors
        sensor = next(cycle_sensors)

        # collect data from currently selected sensor
        sensors.read(sensor)

        # debug
        # ex.dummy()

        # compile data into a JETI EX frame
        frame = ex.ex_frame(sensors.get_data(), type='data')

# start the second thread on core 1
logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())

# run the main loop on core 0
logger.log('info', 'Starting main loop on core 0')
core0()
