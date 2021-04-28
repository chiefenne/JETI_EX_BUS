'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
from machine import I2C, Pin
import ujson

import Logger
import bme280_float as bme280
import MS5611


class I2C_Sensors:
    '''This class represents all sensors attached via I2C
    '''

    def __init__(self):
        # call constructor of JetiEx
        super().__init__()

        self.available_sensors = dict()

        # load information of known sensors 
        self.knownSensors(filename='sensors.json')

        # setup I2C connection to sensors
        self.setupI2C(scl=25, sda=26)

        # get all attached sensors
        self.scanI2C()

        # arm sensors
        self.armSensors()

        # setup a logger for the REPL
        self.logger = Logger.Logger()

    def setupI2C(self, id=1, scl=25, sda=26, freq=400000):
        '''Setup an I2C connection.
        Pins 25 and 26 are the default I2C pins (board dependend)
        '''
        self.i2c = I2C(id, scl=Pin(scl), sda=Pin(sda), freq=freq)

    def knownSensors(self, filename='sensors.json'):
        '''Load id, address, type, etc. of known sensors from json file
        '''
        with open(filename, 'r') as fp:
	        self.known_sensors = ujson.load(fp)

    def scanI2C(self):
        '''Scan all I2C addresses between 0x08 and 0x77 inclusive and
        return a list of those that respond.
        '''

        # the return value per I2C device is its hex address
        addresses = self.i2c.scan()

        # populate available sensors (subset or all of known sensors)
        for address in addresses:
            for sensor_id in self.known_sensors:
                if address in self.known_sensors[sensor_id]['address']:
                    sensor_type = self.known_sensors[sensor_id]['type']
                    self.available_sensors[sensor_id] = {'type': sensor_type,
                                               'address': address}

        return self.available_sensors

    def armSensors(self):
        '''Arm available sensors by attaching their drivers
        '''

        for sensor in self.available_sensors:
            
            if sensor == 'BME280':
                bme280 = bme280.BME280(i2c=self.i2c)
                self.available_sensors[sensor]['reader'] = bme280

            if sensor == 'MS5611':
                ms5611 = MS5611.MS5611(bus=self.i2c)
                self.available_sensors[sensor]['reader'] = ms5611

    def read(self, sensor):
        '''Read data from sensor.

        The data are read in different ways, depending on the snesor (driver)

        Args:
            sensor (str): Sensor id
        '''

        # BME280 pressure sensor
        if 'BME280' in sensor:
            address = self.available_sensors[sensor]['address']
            reader = self.available_sensors[sensor]['reader']
            p, t, h = reader.values()
            message = 'Sensor: {}, Address {},Pressure {}, Temperature {}, \
                       humidity {}'.format(sensor, address, p, t, h)
            self.logger.log('info', message)

            return p, t, h

        # MS5611 pressure sensor
        if 'MS5611' in sensor:
            address = self.available_sensors[sensor]['address']
            reader = self.available_sensors[sensor]['reader']
            reader.read()
            message = 'Sensor: {}, Address {},Pressure {}, Temperature {}'. \
                        format(sensor, address, p, t)
            self.logger.log('info', message)

            return reader.pressureAdj, reader.tempC

