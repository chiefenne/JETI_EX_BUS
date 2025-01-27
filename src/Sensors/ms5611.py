# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`ms5611`
================================================================================

MicroPython Driver for the TE MS5611 Pressure and Temperature Sensor


* Author(s): Jose D. Montoya



A. Ennemoser, 2023-07
Modifications:
    Reduced waiting time for ADC conversion time (original: 15ms)
      - ADC conversion time is 10ms for OSR 4096 according to application note AN520
      - and maximum 9.04ms according to datasheet
    Initializations:
      - initial altitude for relative altitude measurements
      - alpha beta filter for pressure signal smoothing
    Added methods:
      - calc_altitude
      - read_jeti

"""

import time
from micropython import const
# from micropython_ms5611.i2c_helpers import CBits, RegisterStruct
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

_TEMP = const(0x58)
_PRESS = const(0x48)


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

    _pressure = CBits(24, _PRESS, 0, 3, False)
    _temp = CBits(24, _TEMP, 0, 3, False)

    def __init__(self, i2c, address: int = 0x77) -> None:
        self._i2c = i2c
        self._address = address

        self.c1 = self._c1
        self.c2 = self._c2
        self.c3 = self._c3
        self.c4 = self._c4
        self.c5 = self._c5
        self.c6 = self._c6
        self.temperature_oversample_rate = TEMP_OSR_4096
        self.pressure_oversample_rate = PRESS_OSR_4096

        # store initial altitude for relative altitude measurements
        # make an initial averaged measurement
        dummy, pressure = self.measurements # dummy measurement
        num = 10
        self.initial_altitude = 0.0
        self.initial_pressure = 0.0
        for _ in range(num):
            dummy, pressure = self.measurements
            self.initial_pressure += pressure
            self.initial_altitude += self.calc_altitude(pressure)
            time.sleep_ms(10)
        self.initial_pressure /= num
        self.initial_altitude /= num

        # signal filter
        alpha = 0.08
        beta = 0.003
        self.pressure_filter = AlphaBetaFilter(alpha=alpha,
                                               beta=beta,
                                               initial_value=self.initial_pressure,
                                               initial_velocity=0,
                                               delta_t=1)
        alpha = 0.15
        beta = 0.001
        self.altitude_filter = AlphaBetaFilter(alpha=alpha,
                                               beta=beta,
                                               initial_value=self.calc_altitude(self.initial_pressure),
                                               initial_velocity=0,
                                               delta_t=1)

    @property
    def measurements(self) -> Tuple[float, float]:
        """
        Temperature and Pressure
        """
        press_buf = bytearray(3)
        self._i2c.writeto(self._address, bytes([self._pressure_command]))
        time.sleep(0.01) # wait ADC conversion time (10ms for OSR 4096)
        self._i2c.readfrom_mem_into(self._address, _DATA, press_buf)
        D1 = press_buf[0] << 16 | press_buf[1] << 8 | press_buf[0]

        temp_buf = bytearray(3)
        self._i2c.writeto(self._address, bytes([self._temp_command]))
        time.sleep(0.01) # wait ADC conversion time (10ms for OSR 4096)
        self._i2c.readfrom_mem_into(self._address, _DATA, temp_buf)
        D2 = temp_buf[0] << 16 | temp_buf[1] << 8 | temp_buf[0]

        dT = D2 - self.c5 * 2**8.0
        TEMP = 2000 + dT * self.c6 / 2**23.0
        OFF = self.c2 * 2**16.0 + dT * self.c4 / 2**7.0
        SENS = self.c1 * 2**15.0 + dT * self.c3 / 2**8.0

        if TEMP < 2000:
            T2 = dT * dT / 2**31.0
            OFF2 = 5 * (TEMP - 2000) ** 2.0 / 2
            SENS2 = 5 * (TEMP - 2000) ** 2.0 / 4
            if TEMP < -1500:
                OFF2 = OFF2 + 7 * (TEMP + 1500) ** 2.0
                SENS2 = SENS2 + 11 * (TEMP + 1500) ** 2.0 / 2
            TEMP = TEMP - T2
            OFF = OFF - OFF2
            SENS = SENS - SENS2

        P = (SENS * D1 / 2**21.0 - OFF) / 2**15.0

        return TEMP / 100, P

    @property
    def temperature_oversample_rate(self) -> str:
        """
        Sensor temperature_oversample_rate

        +----------------------------------+---------------+
        | Mode                             | Value         |
        +==================================+===============+
        | :py:const:`ms5611.TEMP_OSR_256`  | :py:const:`0` |
        +----------------------------------+---------------+
        | :py:const:`ms5611.TEMP_OSR_512`  | :py:const:`1` |
        +----------------------------------+---------------+
        | :py:const:`ms5611.TEMP_OSR_1024` | :py:const:`2` |
        +----------------------------------+---------------+
        | :py:const:`ms5611.TEMP_OSR_2048` | :py:const:`3` |
        +----------------------------------+---------------+
        | :py:const:`ms5611.TEMP_OSR_4096` | :py:const:`4` |
        +----------------------------------+---------------+
        """
        values = (
            "TEMP_OSR_256",
            "TEMP_OSR_512",
            "TEMP_OSR_1024",
            "TEMP_OSR_2048",
            "TEMP_OSR_4096",
        )
        return values[self._temperature_oversample_rate]

    @temperature_oversample_rate.setter
    def temperature_oversample_rate(self, value: int) -> None:
        if value not in temperature_oversample_rate_values:
            raise ValueError(
                "Value must be a valid temperature_oversample_rate setting"
            )
        self._temperature_oversample_rate = value
        self._temp_command = temp_command_values[value]

    @property
    def pressure_oversample_rate(self) -> str:
        """
        Sensor pressure_oversample_rate

        +-----------------------------------+---------------+
        | Mode                              | Value         |
        +===================================+===============+
        | :py:const:`ms5611.PRESS_OSR_256`  | :py:const:`0` |
        +-----------------------------------+---------------+
        | :py:const:`ms5611.PRESS_OSR_512`  | :py:const:`1` |
        +-----------------------------------+---------------+
        | :py:const:`ms5611.PRESS_OSR_1024` | :py:const:`2` |
        +-----------------------------------+---------------+
        | :py:const:`ms5611.PRESS_OSR_2048` | :py:const:`3` |
        +-----------------------------------+---------------+
        | :py:const:`ms5611.PRESS_OSR_4096` | :py:const:`4` |
        +-----------------------------------+---------------+
        """
        values = (
            "PRESS_OSR_256",
            "PRESS_OSR_512",
            "PRESS_OSR_1024",
            "PRESS_OSR_2048",
            "PRESS_OSR_4096",
        )
        return values[self._pressure_oversample_rate]

    @pressure_oversample_rate.setter
    def pressure_oversample_rate(self, value: int) -> None:
        if value not in pressure_oversample_rate_values:
            raise ValueError("Value must be a valid pressure_oversample_rate setting")
        self._pressure_oversample_rate = value
        self._pressure_command = pressure_command_values[value]

    def calc_altitude(self, pressure):
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

    def read_jeti(self):
        '''Read sensor data'''

        self.temperature, pressure = self.measurements
        self.pressure = self.pressure_filter.update(pressure)  # filter the pressure signal

        self.altitude = self.calc_altitude(self.pressure)
        # self.altitude = self.altitude_filter.update(self.altitude)  # filter the altitude signal

        self.relative_altitude = self.altitude - self.initial_altitude

        return self.pressure, \
            self.temperature, \
            self.altitude, \
            self.relative_altitude
