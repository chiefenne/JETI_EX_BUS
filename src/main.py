'''Python Implementation of the JETI EX Bus protocol

This module holds the overall program logic. It initializes the serial connection
between board and Jeti receiver.

Furter it connects via I2C to the sensors which are attached to the board.

After that it starts an endless loop to handle all data streams between the devices.


Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021


uasyncio related code is taken or derived the work of Peter Hinch:
https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
import uos as os
import uasyncio as asyncio

import pyb

# import JetiExBus
import I2C
import dummy_sensor

# show led for activity
blue = pyb.LED(4)
blue.on()

# instantiate a Jeti ex bus connection (UART)
# exbus = JetiExBus.JetiExBus(baudrate=125000, bits=8, parity=None, stop=1)
# exbus.connect()

# collect hardware attached via I2C
i2c = I2C.Connect()


def set_global_exception():
    '''Exception handler that supports debugging asynchronous applications
    '''
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

async def main():
    # debug aid
    set_global_exception()

    # the constructor creates an asynchronous task
    sensor1 = dummy_sensor.Sensor(1, i2c.bus, read_delay=500)
    sensor2 = dummy_sensor.Sensor(2, i2c.bus, read_delay=1000)
    sensor3 = dummy_sensor.Sensor(3, i2c.bus, read_delay=4000)

    # Wait for devices to be ready
    await sensor1
    await sensor2
    await sensor3

    while True:
        print('Sensor 1 value {}'.format(sensor1.value))
        print('Sensor 2 value {}'.format(sensor2.value))
        print('Sensor 3 value {}'.format(sensor3.value))
        await asyncio.sleep(2)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state
