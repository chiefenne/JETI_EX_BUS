'''BOSCH BME280 sensor class'''


import Sensors.bme280_float as bme280
from Utils.Logger import Logger

class BME280_Sensor():

    def __init__(self, address=0x76, i2c=None):
        '''Constructor

        Parameters
        ----------
        address : int
            I2C address of the sensor
        i2c : I2C
            I2C bus

        '''

        self.name = 'BOSCH BME280'
        self.address = address
        self.i2c = i2c
        # unique device ID used for second (lower) part of the serial number
        self.deviceID = 1
        self._type = 'pressure'

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        return
    
    def arm(self):
        '''Arm the sensors
        '''
        self.sensor = bme280.BME280(address=self.address, i2c=self.i2c)

        return
    
    def read(self, verbose=False):
        '''Read sensor data. Depending on the sensor the data is read
        through the respective driver method.
        '''

        t, p, h = self.sensor.read_compensated_data()
        
        # compile all available sensor data
        self.pressure = p/100.0
        self.temperature = t
        self.humidity = h
        self.altitude = self.sensor.altitude
        # fixme: dew point throws an error (maybe 'log')
        # self.dew_point = self.sensor.dew_point

        # log the data
        if verbose:
            message = 'Sensor {}: Pressure {:.1f} (hPa), Temperature {:.1f} (C), Humidity {:.1f} (%), Altitude {:.1f} (m)'.format(
                self.name,
                self.pressure,
                self.temperature,
                self.humidity,
                self.altitude)
            self.logger.log('info', message)

        return self.pressure, self.temperature, self.humidity
