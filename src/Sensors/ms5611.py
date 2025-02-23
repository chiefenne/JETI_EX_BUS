import micropython
import time
import struct

from Sensors.i2c_helpers import RegisterStruct
import Sensors.ms5611_constants as msc

_POW_2_7 = 128.0
_POW_2_8 = 256.0
_POW_2_15 = 32_768.0
_POW_2_16 = 65_536.0
_POW_2_21 = 2_097_152.0
_POW_2_23 = 8_388_608.0
_POW_2_31 = 2_147_483_648.0


class MS5611:
    _c1 = RegisterStruct(msc.CAL_DATA_C1, ">H")
    _c2 = RegisterStruct(msc.CAL_DATA_C2, ">H")
    _c3 = RegisterStruct(msc.CAL_DATA_C3, ">H")
    _c4 = RegisterStruct(msc.CAL_DATA_C4, ">H")
    _c5 = RegisterStruct(msc.CAL_DATA_C5, ">H")
    _c6 = RegisterStruct(msc.CAL_DATA_C6, ">H")

    def __init__(self, i2c, address) -> None:

        self._i2c = i2c
        self._address = address

        self.c1: int = self._c1 # access the class attribute
        self.c2: int = self._c2
        self.c3: int = self._c3
        self.c4: int = self._c4
        self.c5: int = self._c5
        self.c6: int = self._c6
        self._temp_command = msc.temp_command_values[msc.TEMP_OSR_1024]
        self.conversion_time_temp = msc.conversion_times[msc.TEMP_OSR_1024]
        self._pressure_command = msc.pressure_command_values[msc.PRESS_OSR_4096]
        self.conversion_time_press = msc.conversion_times[msc.PRESS_OSR_4096]

    @micropython.native
    def measure(self):

        c1: int = self.c1
        c2: int = self.c2
        c3: int = self.c3
        c4: int = self.c4
        c5: int = self.c5
        c6: int = self.c6

        # Start temperature conversion
        self._i2c.writeto(self._address, bytes([self._temp_command]))
        time.sleep_ms(self.conversion_time_temp)

        # Read temperature
        temp_buf = bytearray(3)
        self._i2c.readfrom_mem_into(self._address, msc.DATA, temp_buf)
        D2 = struct.unpack(">I", b'\x00' + temp_buf)[0]

        # Start pressure conversion
        self._i2c.writeto(self._address, bytes([self._pressure_command]))
        time.sleep_ms(self.conversion_time_press)

        # Read pressure
        press_buf = bytearray(3)
        self._i2c.readfrom_mem_into(self._address, msc.DATA, press_buf)
        D1 = struct.unpack(">I", b'\x00' + press_buf)[0]

        # Calculate temperature and pressure from the raw values
        dT = D2 - c5 * _POW_2_8
        TEMP = 2000.0 + dT * c6 / _POW_2_23
        OFF = c2 * _POW_2_16 + dT * c4 / _POW_2_7
        SENS = c1 * _POW_2_15 + dT * c3 / _POW_2_8

        # second order temperature compensation
        if TEMP < 2000.0:
            T2 = dT * dT / _POW_2_31
            OFF2 = 2.5 * (TEMP - 2000.0) ** 2.0
            SENS2 = OFF2 / 2.0
            if TEMP < -1500.0:
                T15P2 = (TEMP + 1500.0) ** 2.0
                OFF2 += 7.0 * T15P2
                SENS2 += 5.5 * T15P2
            TEMP -= T2
            OFF -= OFF2
            SENS -= SENS2

        P = (SENS * D1 / _POW_2_21 - OFF) / _POW_2_15

        return P, TEMP / 100.0

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''

        self.pressure, self.temperature = self.measure()
        return self.pressure, self.temperature
