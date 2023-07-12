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

# setup the led
if 'rp2' in sys.platform:
    ledg = Pin(19, Pin.OUT)

# lock object used to prevent other cores from accessing shared resources
lock = _thread.allocate_lock()

# shared variable to indicate whether the main thread is still running
main_thread_running = True

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
    global main_thread_running

    # debug
    # exbus.dummy()

    try:
        ledg.value(0)
        exbus.run_forever()
    
    except KeyboardInterrupt:
        # Set the flag to indicate that the main thread is not running
        main_thread_running = False

        # inform the user
        logger.log('info', 'Keyboard interrupt occurred')
        logger.log('info', 'Stopping main thread on core 0')    

        # switch off the green led
        ledg.value(1)

        _thread.exit()
    
    # except Exception as e:
    #     # Set the flag to indicate that the main thread is not running
    #     main_thread_running = False
    #     logger.log('error', '{}'.format(e))
    # 
    #     # switch off the green led
    #     ledg.value(1)
    # 
    #     _thread.exit()

    # exit if the main thread is not running anymore
    _thread.exit()

# function which is run on core 1
def core1():
    global main_thread_running

    # make a generator out of the list of sensors
    cycle_sensors = cycler(sensors.get_sensors())

    # get the first sensor
    sensor = next(cycle_sensors)

    #
    device_sent = False
    ex.exbus_device_ready = False
    ex.exbus_data_ready = False
    ex.exbus_text1_ready = False
    ex.exbus_text2_ready = False
    
    while main_thread_running:

        # cycle infinitely through all sensors
        sensor = next(cycle_sensors)

        # collect data from currently selected sensor
        # the "read_jeti" method has to be implemented sensor specific
        # e.g., see Sensors/bme280_float.py
        sensor.read_jeti()

        ex.lock.acquire()

        # update data frame (new sensor data)
        # 2 values per data frame, 1 value per text frame (so 2 text frames per data frame)
        # FIXME: data are hardcoded for testing purposes
        # FIXME: data are hardcoded for testing purposes
        # FIXME: data are hardcoded for testing purposes
        telemetry_1 = 'CLIMB'
        telemetry_2 = 'REL_ALTITUDE'

        if device_sent:
            ex.exbus_data, _ = ex.exbus_frame(sensor, frametype='data', data_1=telemetry_1, data_2=telemetry_2)
            ex.exbus_text1, _ = ex.exbus_frame(sensor, frametype='text', text=telemetry_1)
            ex.exbus_text2, _ = ex.exbus_frame(sensor, frametype='text', text=telemetry_2)

            ex.exbus_data_ready = True
            ex.exbus_text1_ready = True
            ex.exbus_text2_ready = True
        else:
            # send the device name first
            ex.exbus_device, _ = ex.exbus_frame(sensor, frametype='text', text='DEVICE')
            ex.exbus_device_ready = True
            device_sent = True
            logger.log('info', 'DEVICE information prepared')

        ex.lock.release()

    # inform the user that the second thread is stopped
    logger.log('info', 'Stopping second thread on core 1')
 
    # switch off the green led
    ledg.value(1)


# start the second thread on core 1
# logger.log('info', 'Starting second thread on core 1')
second_thread = _thread.start_new_thread(core1, ())

# run the main loop on core 0
logger.log('info', 'Starting main loop on core 0')
core0()
