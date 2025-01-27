
from Utils.Logger import Logger


class DemoSensor:

    def __init__(self, address=0x99, i2c=None):
        self.address = address
        self.i2c = i2c
        self.counter = 0
        self.sign = 1

    def read_jeti(self):
        '''Read demo sensor. Create fake data for testing purposes.'''

        self.counter += 1
        if self.counter % 20 == 0:
            self.sign = -1 * self.sign

        # compile all available sensor data
        self.pressure = 97734.0 + self.counter * 2 * self.sign
        self.temperature = 29.37 + self.counter * 0.1 * self.sign
        self.humidity = 45.67 + self.counter * 0.5 * self.sign
        self.altitude = 1234.5 + self.counter * 10 * self.sign
        self.relative_altitude = self.altitude

        # log the data for debugging purposes
        logger = Logger(prestring='JETI DEMO')
        logger.log('info', 'Pressure: {}'.format(self.pressure))
        logger.log('info', 'Temperature: {}'.format(self.temperature))
        logger.log('info', 'Humidity: {}'.format(self.humidity))
        logger.log('info', 'Altitude: {}'.format(self.altitude))

        return self.pressure, self.temperature, self.humidity, self.altitude
