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

import JetiExBus
import I2C
import HTU21D

# show led for activity
blue = pyb.LED(4)
blue.on()

# instantiate a Jeti ex bus connection
exbus = JetiExBus.JetiExBus(baudrate=125000, bits=8, parity=None, stop=1)
exbus.connect()

# collect sensors attached via I2C
i2c_sensors = I2C.Devices()

# transfer sensor meta data
exbus.Sensors(i2c_sensors)


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
    set_global_exception()  # Debug aid
    htu = HTU21D(I2C(1))  # Constructor creates task
    await htu  # Wait for device to be ready (implicitly calls __iter__ ???)
    while True:
        fstr = 'Temp {:5.1f} Humidity {:5.1f}'
        print(fstr.format(htu.temperature, htu.humidity))
        await asyncio.sleep(5)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state
