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

import pyb

import JetiExBus
import JetiSensor

# show led for activity
blue = pyb.LED(4)
blue.on()

# instantiate a Jeti ex bus connection
exbus = JetiExBus.JetiExBus(baudrate=125000, bits=8, parity=None, stop=1)

# establish the serial connection
exbus.connect()

# collect sensors attached via I2C
i2c_sensors = JetiSensor.I2C_Sensors()

# transfer sensor meta data
exbus.Sensors(i2c_sensors)

# run JETI Ex Bus
exbus.run_forever()
