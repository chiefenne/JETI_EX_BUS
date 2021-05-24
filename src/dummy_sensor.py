# based on htu21d_mc.py. Copyright Peter Hinch 2018-2020 Released under the MIT license

import uasyncio as asyncio
from micropython import const

_PAUSE_MS = const(60)  # sensor acquisition delay


class Sensor:

    def __init__(self, id, i2c_bus, read_delay=10):
        self.i2c = i2c_bus
        self.value = None
        self.id = id
        self.current_sensor_value = self.id * 10.0

        asyncio.create_task(self._run(read_delay))

    async def _run(self, read_delay):

        while True:
            # 
            self.value = await self._get_data()

            await asyncio.sleep_ms(read_delay)

    def __iter__(self):
        '''This class is called exactly once (see iterators)
        Await 1st reading
        '''
        while self.value is None:
            # wait on other running tasks (one of them being the _run function of this class)
            # 0 delay to be instantly back on scheduler stack "fair round-robin"
            yield from asyncio.sleep_ms(0)

    async def _get_data(self):
        
        await asyncio.sleep_ms(_PAUSE_MS)  # Wait for device

        # simulate changing values
        self.current_sensor_value += 0.2
        return self.current_sensor_value
