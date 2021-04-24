'''Setup I2C to check for and attach to I2C based sensors
'''

from machine import I2C, Pin


class I2C_Sensors:
    '''Handle I2C connections
    '''

    def __init__(self, id=1, scl=25, sda=26, freq=400000):

        # pin25 and pin26 are the default I2C pins (this is board dependend)
        self.i2c = I2C(id, scl=Pin(scl), sda=Pin(sda), freq=freq)

    def scan(self):
        '''Scan all I2C addresses between 0x08 and 0x77 inclusive and
        return a list of those that respond.
        These are all sensors which are connected via I2C.
        '''
        self.sensors = self.i2c.scan()