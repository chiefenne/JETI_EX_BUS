import micropython
import time
import struct

try:
    from typing import Tuple
except ImportError:
    pass

from Sensors.i2c_helpers import CBits, RegisterStruct
import Sensors.ms5611_constants as msc


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
                 temperature_oversample_rate=msc.TEMP_OSR_1024,
                 pressure_oversample_rate=msc.PRESS_OSR_4096) -> None:
        self._i2c = i2c
        self._address = address

        self.c1 = self._c1
        self.c2 = self._c2
        self.c3 = self._c3
        self.c4 = self._c4
        self.c5 = self._c5
        self.c6 = self._c6
        self._temp_command = msc.temp_command_values[temperature_oversample_rate]
        self._pressure_command = msc.pressure_command_values[pressure_oversample_rate]
        self.conversion_time_temp = msc.conversion_times[temperature_oversample_rate]
        self.conversion_time_press = msc.conversion_times[pressure_oversample_rate]

        self.buffer_size = 10
        self.buffer = [(0.0, 0.0)] * self.buffer_size
        self.buffer_index = 0

        self._periodic_sensor_reading() # Start the periodic task

    @micropython.native
    def _periodic_sensor_reading(self):
        state = 0
        d1 = 0
        d2 = 0
        while True: # Check the running flag to allow stopping

            if state == 0:
                # Start temperature conversion
                self._i2c.writeto(self._address, bytes([self._temp_command]))
                time.sleep_ms(self.conversion_time_temp)
                state = 1
            elif state == 1:
                # Read temperature
                temp_buf = bytearray(3)
                self._i2c.readfrom_mem_into(self._address, msc._DATA, temp_buf)
                d2 = struct.unpack(">I", b'\x00' + temp_buf)[0]

                # Start pressure conversion
                self._i2c.writeto(self._address, bytes([self._pressure_command]))
                time.sleep_ms(self.conversion_time_press)
                state = 2
            elif state == 2:
                # Read pressure
                press_buf = bytearray(3)
                self._i2c.readfrom_mem_into(self._address, msc._DATA, press_buf)
                d1 = struct.unpack(">I", b'\x00' + press_buf)[0]

                # Store press and temp in buffer
                self.data = self._calculate_and_store(d1, d2)
                state = 0

    @micropython.native
    def _calculate_and_store_native(self, d1: int, d2: int) -> None:
        """
        Calculates temperature and pressure from raw sensor readings and stores them in the buffer.
        Optimized with @micropython.native decorator.
        """
        c1: int = self.c1
        c2: int = self.c2
        c3: int = self.c3
        c4: int = self.c4
        c5: int = self.c5
        c6: int = self.c6
        buffer_index: int = self.buffer_index # Keep type hints for index and size
        buffer_size: int = self.buffer_size
        lock = self.lock # lock is a standard Python object, no type hint needed

        dT: float = float(d2 - c5 * 256) # Explicitly cast to float to ensure float arithmetic. Corrected calculation to use c5
        TEMP: float = 2000.0 + dT * c6 / 8388608.0 # Keep float type hint for TEMP and other float variables
        OFF: float = float(c2 * 65536 + dT * c4 / 128.0) # Explicit cast and corrected calculation to use c2
        SENS: float = float(c1 * 32768 + dT * c3 / 256.0) # Explicit cast and corrected calculation to use c1

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

        with lock:
            # updating the buffer
            self.buffer[buffer_index] = (TEMP / 100.0, P)
            self.buffer_index = (buffer_index + 1) % buffer_size

    @micropython.native
    def get_lock(self, lock):
        self.lock = lock

    @micropython.native
    def _read_buffer(self) -> Tuple[float, float]:
        lock = self.lock
        with lock:
            # Read the most recent value from the buffer
            temp, press = self.buffer[(self.buffer_index - 1) % self.buffer_size]
            return temp, press

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''
        self.temperature, self.pressure = self._read_buffer()
        return self.pressure, self.temperature
