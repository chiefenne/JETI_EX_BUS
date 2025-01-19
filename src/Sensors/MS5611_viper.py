import time
from micropython import const, native, viper
import struct
from Sensors.i2c_helpers import CBits, RegisterStruct
from Utils.alpha_beta_filter import AlphaBetaFilter

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


class MS5611:
    """Driver for the MS5611 Sensor connected over I2C.

    :param ~machine.I2C i2c: The I2C bus the MS5611 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x77`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`MS5611` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        from machine import Pin, I2C
        from micropython_ms5611 import ms5611

    Once this is done you can define your `machine.I2C` object and define your sensor object

    .. code-block:: python

        i2c = I2C(1, sda=Pin(2), scl=Pin(3))
        ms = ms5611.MS5611(i2c)

    Now you have access to the attributes

    .. code-block:: python

        temp = ms.temperature
        press = ms.pressure

    """

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

        # store initial altitude for relative altitude measurements
        # make an initial averaged measurement
        dummy, pressure = self._read_raw_measurements()  # dummy measurement
        time.sleep_ms(100)
        num = 30
        initial_altitude = 0.0
        initial_pressure = 0.0
        for _ in range(num):
            dummy, pressure = self._read_raw_measurements()
            initial_pressure += pressure
            initial_altitude += self._calc_altitude(pressure)
            time.sleep_ms(20)
        initial_pressure /= num
        initial_altitude /= num

        # signal filter
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


    @micropython.viper
    def _read_raw_measurements(self) -> Tuple[float, float]:
        i2c: object = self._i2c
        address: int = self._address

        press_buf: bytearray = bytearray(3)
        i2c.writeto(address, bytes([self._pressure_command]))
        time.sleep_ms(15)
        i2c.readfrom_mem_into(address, _DATA, press_buf)
        D1: int = struct.unpack(">I", b'\x00' + press_buf)[0]

        temp_buf: bytearray = bytearray(3)
        i2c.writeto(address, bytes([self._temp_command]))
        time.sleep_ms(15)
        i2c.readfrom_mem_into(address, _DATA, temp_buf)
        D2: int = struct.unpack(">I", b'\x00' + temp_buf)[0]

        dT: float = D2 - self._c5 * 256.0
        TEMP: float = 2000 + dT * self._c6 / 8388608.0
        OFF: float = self._c2 * 65536.0 + dT * self._c4 / 128.0
        SENS: float = self._c1 * 32768.0 + dT * self._c3 / 256.0
        
        
        if TEMP < 2000:
            T2: float = dT * dT / 2147483648.0
            OFF2: float = 5 * (TEMP - 2000) ** 2.0 / 2
            SENS2: float = 5 * (TEMP - 2000) / 4
            if TEMP < -1500:
                OFF2 = OFF2 + 7 * (TEMP + 1500) ** 2.0
                SENS2 = SENS2 + 11 * (TEMP + 1500) / 2
            TEMP = TEMP - T2
            OFF = OFF - OFF2
            SENS = SENS - SENS2

        P: float = (SENS * D1 / 2097152.0 - OFF) / 32768.0
        
        return TEMP / 100, P

    @micropython.native
    def _calc_altitude(self, pressure):
        '''The following variables are constants for a standard atmosphere
        t0 = 288.15 # sea level standard temperature (K)
        p0 = 101325.0 # sea level standard atmospheric pressure (Pa)
        gamma = 6.5 / 1000.0 # temperature lapse rate (K / m)
        g = 9.80665 # gravity constant (m / s^2)
        R = 8.314462618 # mol gas constant (J / (mol * K))
        Md = 28.96546e-3 # dry air molar mass (kg / mol)
        Rd =  R / Md
        return (t0 / gamma) * (1.0 - (pressure / p0)**(Rd * gamma / g))
        '''
        return 44330.76923 * (1.0 - (pressure / 101325.0)**0.19025954)

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''
        temperature, pressure = self._read_raw_measurements()
        filtered_pressure = self.pressure_filter.update(pressure) # filter the pressure signal
        altitude = self._calc_altitude(filtered_pressure) # calculate altitude from filtered pressure
        # altitude = self.altitude_filter.update(altitude)  # filter the altitude signal
        relative_altitude = altitude - self.initial_altitude

        return filtered_pressure, temperature, altitude, relative_altitude

    @property
    def temperature(self) -> float:
        return self._read_raw_measurements()[0]

    @property
    def pressure(self) -> float:
       return self._read_raw_measurements()[1]

    @property
    def altitude(self) -> float:
         return self._calc_altitude(self._read_raw_measurements()[1])

    @property
    def relative_altitude(self) -> float:
        return self._calc_altitude(self._read_raw_measurements()[1]) - self.initial_altitude