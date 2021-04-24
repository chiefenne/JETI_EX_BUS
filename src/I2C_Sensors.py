'''Setup I2C to check for and attach to I2C based sensors
'''

from machine import I2C, Pin


class I2C_Sensors:
    '''Handle I2C connections
    '''

    def __init__(self, id=1, scl=25, sda=26, freq=400000):

        # known sensors and their I2C addresses
        # this of course MUST be checked
        self.known_sensors = {'pressure': {'0x76': 'BME280', '0x77': 'MS5611'},
                              'gps': {'0x42': 'NEO-M8'}}

        self.sensors = dict()

        # pin25 and pin26 are the default I2C pins (this is board dependend)
        self.i2c = I2C(id, scl=Pin(scl), sda=Pin(sda), freq=freq)

    def scan(self):
        '''Scan all I2C addresses between 0x08 and 0x77 inclusive and
        return a list of those that respond.
        '''

        # the return value per I2C device is its hex address
        addresses = self.i2c.scan()

        # populate available sensors (subset or all of known sensors)
        for address in addresses:
            for key in self.known_sensors.keys():
                if address in self.known_sensors[key].keys():
                    self.sensors[key] = {address: self.known_sensors[key][address]}

        return self.sensors

    