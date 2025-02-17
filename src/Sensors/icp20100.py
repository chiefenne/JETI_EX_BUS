import micropython
import time
import struct

# --- Register Definitions (from ICP201xx.h) ---
WHO_AM_I          = 0x75
RESET             = 0x6B
STATUS            = 0x1B
CONFIG            = 0x1A
FIFO_CONFIG       = 0x38
FIFO_COUNT_H      = 0x39
FIFO_DATA         = 0x3A
TEMP_OUT_L        = 0x28
TEMP_OUT_H        = 0x29
PRESS_OUT_L       = 0x2B
PRESS_OUT_H       = 0x2C
# --- End Register Definitions ---

class ICP20100:
    """Class for the TDK ICP-20100 pressure sensor."""

    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address
        self.chip_id = 0

    def _read_byte(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _read_bytes(self, reg, num_bytes):
        return self.i2c.readfrom_mem(self.address, reg, num_bytes)

    def _write_byte(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    def reset(self):
        """Resets the sensor."""
        self._write_byte(RESET, 0x80) # Corrected register name
        time.sleep_ms(10)

    def who_am_i(self):
        """Reads and returns the WHO_AM_I register value."""
        return self._read_byte(WHO_AM_I)

    def begin(self):
        """Initializes the sensor."""
        self.reset()
        self.chip_id = self.who_am_i()
        if self.chip_id != 0x66:  # Expected WHO_AM_I value (verified from the .h file)
            raise Exception("ICP-20100 not found or incorrect WHO_AM_I value: 0x{:02X}".format(self.chip_id))

        # Basic configuration (from Arduino begin())
        self._write_byte(CONFIG, 0x00)  # No filter, ODR = 8 kHz

    def get_pressure_raw(self):
        """Reads and returns the raw pressure data."""
        data = self._read_bytes(PRESS_OUT_L, 2)
        pressure_raw = struct.unpack("<h", data)[0]  # Little-endian, signed short
        return pressure_raw

    def get_temperature_raw(self):
        """Reads and returns the raw temperature data."""
        data = self._read_bytes(TEMP_OUT_L, 2)
        temperature_raw = struct.unpack("<h", data)[0]  # Little-endian, signed short
        return temperature_raw

    def get_pressure_Pa(self):
        """Reads and returns the pressure in kPa (kilopascals)."""
        data_press = self.get_pressure_raw()

        # Sign extension
        if data_press & 0x0800:  # Note: shifted down 11 bits from the original expression 0x080000 because 16 bit value here
            data_press |= 0xF000  # shifted down from 0xFFF00000

        pressure = ((float)(data_press) * 40 / 131072) + 70
        return pressure * 1000  # Convert to Pa

    def get_temperature_C(self):
        """Reads and returns the temperature in degrees Celsius."""
        data_temp = self.get_temperature_raw()

        # Sign extension
        if data_temp & 0x0800:  # Note: shifted down 11 bits from the original expression 0x080000 because 16 bit value here
            data_temp |= 0xF000  # shifted down from 0xFFF00000

        temperature = ((float)(data_temp) * 65 / 262144) + 25
        return temperature

    @micropython.native
    def read_jeti(self):
        '''Read sensor data'''

        self.pressure, self.temperature = self.get_pressure_Pa(), self.get_temperature_C()
        return self.pressure, self.temperature
