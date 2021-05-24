# based on htu21d_mc.py
# Author: Peter Hinch
# Copyright Peter Hinch 2018-2020 Released under the MIT license

import machine
import ustruct
import uasyncio as asyncio
from micropython import const

_PAUSE_MS = const(60)  # sensor acquisition delay


class DUMMY_SENSOR:

    def __init__(self, id, i2c_bus, read_delay=10):
        self.i2c = i2c_bus
        self.value = None
        self.id = id
        asyncio.create_task(self._run(read_delay))

    async def _run(self, read_delay):

        while True:
            # 
            self.value = self._get_data()

            await asyncio.sleep(read_delay)

    def __iter__(self):  # Await 1st reading
        while self.value is None:
            # yield without delay to be instantly back on scheduler stack
            print('Reading NONE from sensor {}'.format(self.id))
            yield from asyncio.sleep(0)

    async def _get_data(self):

        
        await asyncio.sleep_ms(_PAUSE_MS)  # Wait for device
        await asyncio.sleep_ms(_PAUSE_MS)  # Wait for device

        # simulate global warming
        value = self.id * 10.0 + 0.2
        return value
