import _thread
import micropython
from micropython import const
import struct
import machine

try:
    from typing import Tuple
except ImportError:
    pass

from Sensors.i2c_helpers import CBits, RegisterStruct
import MS5611_constants as msc


_POW_2_31 = 2147483648.0
_POW_2_21 = 2097152.0


class MS5611:
    _c1 = RegisterStruct(msc._CAL_DATA_C1, ">H")
    _c2 = RegisterStruct(msc._CAL_DATA_C2, ">H")
    _c3 = RegisterStruct(msc._CAL_DATA_C3, ">H")
    _c4 = RegisterStruct(msc._CAL_DATA_C4, ">H")
    _c5 = RegisterStruct(msc._CAL_DATA_C5, ">H")
    _c6 = RegisterStruct(msc._CAL_DATA_C6, ">H")

    def __init__(self, i2c, address: int = 0x77,
                 temperature_oversample_rate=msc.TEMP_OSR_4096,
                 pressure_oversample_rate=msc.PRESS_OSR_4096) -> None:
        self._i2c = i2c
        self._address = address

        self.c1 = self._c1
        self.c2 = self._c2
        self.c3 = self._c3
        self.c4 = self._c4
        self.c5 = self._c5
        self.c6 = self._c6
        self._temp_command = temp_command_values[temperature_oversample_rate]
        self._pressure_command = pressure_command_values[pressure_oversample_rate]

        self._temp_osr = temperature_oversample_rate
        self._press_osr = pressure_oversample_rate
        self.conversion_time_temp = conversion_times[temperature_oversample_rate]
        self.conversion_time_press = conversion_times[pressure_oversample_rate]

        # Circular buffer for storing results
        self.buffer_size = 5
        self.buffer = [(0.0, 0.0)] * self.buffer_size
        self.buffer_index = 0
        self.buffer_lock = _thread.allocate_lock()

        # Timer setup
        self.timer = machine.Timer()
        self.timer_period = (self.conversion_time_temp + self.conversion_time_press) # Total period in milliseconds
        self.timer.init(period=self.timer_period, mode=machine.Timer.PERIODIC, callback=self._timer_callback)

        self.state = 0 # 0 for temperature, 1 for pressure
        self.d1 = 0
        self.d2 = 0

    def _timer_callback(self, timer):
        if self.state == 0:
            # Start temperature conversion
            self._i2c.writeto(self._address, bytes([self._temp_command]))
            self.state = 1
        elif self.state == 1:
            # Read temperature
            temp_buf = bytearray(3)
            self._i2c.readfrom_mem_into(self._address, msc._DATA, temp_buf)
            self.d2 = struct.unpack(">I", b'\x00' + temp_buf)[0]
            # Start pressure conversion
            self._i2c.writeto(self._address, bytes([self._pressure_command]))
            self.state = 2
        elif self.state == 2:
            # Read pressure
            press_buf = bytearray(3)
            self._i2c.readfrom_mem_into(self._address, msc._DATA, press_buf)
            self.d1 = struct.unpack(">I", b'\x00' + press_buf)[0]
            self._calculate_and_store()
            self.state = 0

    @micropython.viper
    def _calculate_and_store(self) -> None:
        d1: int = self.d1
        d2: int = self.d2
        c1: int = self.c1
        c2: int = self.c2
        c3: int = self.c3
        c4: int = self.c4
        c5: int = self.c5
        c6: int = self.c6
        buffer_index: int = self.buffer_index
        buffer_size: int = self.buffer_size

        dT: float = d2 - c5 * 256.0
        TEMP: float = 2000.0 + dT * c6 / 8388608.0
        OFF: float = c2 * 65536.0 + dT * c4 / 128.0
        SENS: float = c1 * 32768.0 + dT * c3 / 256.0

        if TEMP < 2000.0:
            T2: float = dT * dT / _POW_2_31
            OFF2: float = 5.0 * (TEMP - 2000.0) ** 2.0 / 2.0
            SENS2: float = 5.0 * (TEMP - 2000.0) / 4.0
            if TEMP < -1500.0:
                OFF2 += 7.0 * (TEMP + 1500.0) ** 2.0
                SENS2 += 11.0 * (TEMP + 1500.0) / 2.0
            TEMP -= T2
            OFF -= OFF2
            SENS -= SENS2

        P: float = (SENS * d1 / _POW_2_21 - OFF) / 32768.0

        # Acquire lock before updating the buffer
        self.buffer_lock.acquire()
        self.buffer[buffer_index] = (TEMP / 100.0, P)
        self.buffer_index = (buffer_index + 1) % buffer_size
        self.buffer_lock.release()

    @micropython.native
    def _read_raw_measurements(self) -> Tuple[float, float]:
        # Read the most recent value from the buffer
        self.buffer_lock.acquire()
        temp, press = self.buffer[(self.buffer_index - 1) % self.buffer_size]
        self.buffer_lock.release()
        return temp, press

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''
        temperature, pressure = self._read_raw_measurements()
        return pressure, temperature
