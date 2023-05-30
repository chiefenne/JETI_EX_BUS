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
s = Serial(port=0, baudrate=125000, bits=8, parity=None, stop=1)
serial = s.connect()

# write 1 second of the serial stream to a text file for debugging purposes
DEBUG = True
if DEBUG:
    logger.log('debug', 'Starting to record EX Bus stream ...')
    saveStream(serial, filename='EX_Bus_stream.txt', duration=3000)
    logger.log('debug', 'EX Bus stream recorded')


# setup the I2C bus (pins are board specific)
#    TINY2040 board: GPIO6, GPIO7 at port 1 (id=1)
i2c = I2C_bus(1, scl=Pin(7), sda=Pin(6), freq=400000)
addresses = i2c.scan()

# check for sensors attached to the microcontroller
sensors = Sensors(addresses, i2c.i2c)

# setup the JETI EX protocol
ex = Ex(sensors)

# setup the JETI EX BUS protocol
exbus = ExBus(serial, sensors, ex)

# function which is run on core 0
def core0():
    global main_thread_running

    # debug
    # exbus.dummy()

    try:
        exbus.run_forever()
    
    except KeyboardInterrupt:
        # Keyboard interrupt occurred
        main_thread_running = False  # Set the flag to indicate that the main thread is not running

        # inform the user
        logger.log('info', 'Keyboard interrupt occurred')
        logger.log('info', 'Stopping main thread on core 0')    

        _thread.exit()

# function which is run on core 1
def core1():
    global main_thread_running

    # make a generator out of the list of sensors
    cycle_sensors = cycler(sensors.get_sensors())

    # counter
    i = 0
    
    while main_thread_running:

        # cycle infinitely through all sensors
        sensor = next(cycle_sensors)

        # debug
        verbose = False
        if i % 100 == 0:
            verbose = True

        # collect data from currently selected sensor
        sensor.read(verbose=verbose)

        # debug
        # ex.dummy()

        # send device frame only once
        ex.lock()
        ex.exbus_device = ex.exbus_frame(sensor, frametype='device')
        ex.release()

        # update data frame (new sensor data)
        ex.lock()
        ex.exbus_data = ex.exbus_frame(sensor, frametype='data')
        ex.exbus_data_ready = True
        ex.release()

        # send text frame (only if packet id changed)
        ex.lock()
        ex.exbus_text = ex.exbus_frame(sensor, frametype='text')
        ex.exbus_text_ready = True
        ex.release()

        # debug
        i += 1
        if i % 100 == 0:
            print('EX BUS data: {}'.format(ex.exbus_data))
            print('EX BUS text: {}'.format(ex.exbus_text))

    # inform the user that the second thread is stopped
    logger.log('info', 'Stopping second thread on core 1')

# Shared variable to indicate whether the main thread is still running
main_thread_running = True

# start the second thread on core 1
# logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())

# run the main loop on core 0
logger.log('info', 'Starting main loop on core 0')
core0()
