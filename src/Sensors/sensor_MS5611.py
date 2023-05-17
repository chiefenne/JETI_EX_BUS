'''AMSYS MS5611 sensor class'''


import Sensors.MS5611 as ms5611
from Utils.Logger import Logger

class MS5611_Sensor():

    def __init__(self, address=0x77, i2c=None, elevation=0):
        '''Constructor

        Parameters
        ----------
        address : int
            I2C address of the sensor
        i2c : I2C
            I2C bus

        '''

        self.name = 'AMSYS MS5611'
        self.address = address
        self.i2c = i2c
        # unique device ID used for second (lower) part of the serial number
        self.deviceID = 2
        self.type = 'pressure'

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        return
    
    def arm(self):
        '''Arm the sensors
        '''

        self.sensor = ms5611.MS5611(bus=self.i2c, i2c=self.address, elevation = 0)

        return
    
    def read(self):
        '''Read sensor data. Depending on the sensor the data is read
        through the respective driver method.
        '''

        self.sensor.read()

        self.pressure = self.sensor.pressure
        self.pressureAdj = self.sensor.pressureAdj
        self.temperature = self.sensor.tempC

        message = 'Sensor {}: Pressure {:.1f} (hPa), Temperature {:.1f} (C)'.format(self.name, self.pressureAdj, self.temperature)
        self.logger.log('info', message)

        return self.pressure, self.temperature
