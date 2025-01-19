import time
import micropython
from micropython import const
import struct
from Sensors.i2c_helpers import CBits, RegisterStruct
from Utils.alpha_beta_filter import AlphaBetaFilter
import machine

try:
    from typing import Tuple
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/jposada202020/MicroPython_MS5611.git"

_CAL_DATA_C1 = const(0xA2)
_CAL_DATA_C2 = const(0xA4)
_CAL_DATA_C3 = const(0xA6)
_CAL_DATA_C4 = const(0xA8)
_CAL_DATA_C5 = const(0xAA)
_CAL_DATA_C6 = const(0xAC)
_DATA = const(0x00)

TEMP_OSR_256 = const(0)
TEMP_OSR_512 = const(1)
TEMP_OSR_1024 = const(2)
TEMP_OSR_2048 = const(3)
TEMP_OSR_4096 = const(4)
temperature_oversample_rate_values = (
    TEMP_OSR_256,
    TEMP_OSR_512,
    TEMP_OSR_1024,
    TEMP_OSR_2048,
    TEMP_OSR_4096,
)
temp_command_values = {
    TEMP_OSR_256: 0x50,
    TEMP_OSR_512: 0x52,
    TEMP_OSR_1024: 0x54,
    TEMP_OSR_2048: 0x56,
    TEMP_OSR_4096: 0x58,
}

PRESS_OSR_256 = const(0)
PRESS_OSR_512 = const(1)
PRESS_OSR_1024 = const(2)
PRESS_OSR_2048 = const(3)
PRESS_OSR_4096 = const(4)
pressure_oversample_rate_values = (
    PRESS_OSR_256,
    PRESS_OSR_512,
    PRESS_OSR_1024,
    PRESS_OSR_2048,
    PRESS_OSR_4096,
)
pressure_command_values = {
    PRESS_OSR_256: 0x40,
    PRESS_OSR_512: 0x42,
    PRESS_OSR_1024: 0x44,
    PRESS_OSR_2048: 0x46,
    PRESS_OSR_4096: 0x48,
}

# Conversion times for each oversampling rate (in milliseconds)
conversion_times = {
    TEMP_OSR_256: 1,
    TEMP_OSR_512: 2,
    TEMP_OSR_1024: 3,
    TEMP_OSR_2048: 5,
    TEMP_OSR_4096: 10,
    PRESS_OSR_256: 1,
    PRESS_OSR_512: 2,
    PRESS_OSR_1024: 3,
    PRESS_OSR_2048: 5,
    PRESS_OSR_4096: 10,
}

_POW_2_31 = 2147483648.0
_POW_2_21 = 2097152.0


class MS5611:
    _c1 = RegisterStruct(_CAL_DATA_C1, ">H")
    _c2 = RegisterStruct(_CAL_DATA_C2, ">H")
    _c3 = RegisterStruct(_CAL_DATA_C3, ">H")
    _c4 = RegisterStruct(_CAL_DATA_C4, ">H")
    _c5 = RegisterStruct(_CAL_DATA_C5, ">H")
    _c6 = RegisterStruct(_CAL_DATA_C6, ">H")

    def __init__(self, i2c, address: int = 0x77,
                 temperature_oversample_rate=TEMP_OSR_4096,
                 pressure_oversample_rate=PRESS_OSR_4096) -> None:
        self._i2c = i2c
        self._address = address

        self._c1 = self._c1
        self._c2 = self._c2
        self._c3 = self._c3
        self._c4 = self._c4
        self._c5 = self._c5
        self._c6 = self._c6
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

        # Initial calibration and filtering setup...
        dummy, pressure = self._read_raw_measurements()
        time.sleep_ms(100)
        num = 10
        initial_altitude = 0.0
        initial_pressure = 0.0
        for _ in range(num):
            dummy, pressure = self._read_raw_measurements()
            initial_pressure += pressure
            initial_altitude += self._calc_altitude(pressure)
            time.sleep_ms(10)
        initial_pressure /= num
        initial_altitude /= num

        alpha = 0.08
        beta = 0.003
        self.pressure_filter = AlphaBetaFilter(alpha=alpha,
                                               beta=beta,
                                               initial_value=initial_pressure,
                                               initial_velocity=0,
                                               delta_t=0.02)
        alpha = 0.15
        beta = 0.001
        self.altitude_filter = AlphaBetaFilter(alpha=alpha,
                                               beta=beta,
                                               initial_value=self._calc_altitude(initial_pressure),
                                               initial_velocity=0,
                                               delta_t=0.02)
        self.initial_altitude = initial_altitude

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
            self._i2c.readfrom_mem_into(self._address, _DATA, temp_buf)
            self.d2 = struct.unpack(">I", b'\x00' + temp_buf)[0]
            # Start pressure conversion
            self._i2c.writeto(self._address, bytes([self._pressure_command]))
            self.state = 2
        elif self.state == 2:
            # Read pressure
            press_buf = bytearray(3)
            self._i2c.readfrom_mem_into(self._address, _DATA, press_buf)
            self.d1 = struct.unpack(">I", b'\x00' + press_buf)[0]
            self._calculate_and_store()
            self.state = 0

    @micropython.viper
    def _calculate_and_store(self) -> None:
        d1: int = self.d1
        d2: int = self.d2
        c1: int = self._c1
        c2: int = self._c2
        c3: int = self._c3
        c4: int = self._c4
        c5: int = self._c5
        c6: int = self._c6
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
    def _calc_altitude(self, pressure):
        return 44330.76923 * (1.0 - (pressure / 101325.0)**0.19025954)

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''
        temperature, pressure = self._read_raw_measurements()
        return pressure, temperature, self.initial_altitude
