'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
from machine import I2C, Pin
import ujson

import Sensors.bme280_float as bme280
import Sensors.MS5611 as MS5611
from Utils.Logger import Logger


class Sensors:
    '''This class represents all sensors attached via I2C
    '''

    def __init__(self):
        # call constructor of JetiEx
        super().__init__()

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        self.available_sensors = dict()

        # load information of known sensors 
        self.knownSensors()

        # setup I2C connection
        # TINY2040 GPIO6, GPIO7
        sda = Pin(6)
        scl = Pin(7)
        self.setupI2C(1, scl, sda, freq=400000)

        # get all attached sensors
        self.scanI2C()
       
        # number of sensors attached
        message = 'Number of sensors attached: {}'.format(len(self.available_sensors))
        self.logger.log('info', message)

        # arm sensors
        self.armSensors()

    def setupI2C(self, id, scl, sda, freq=100000):
        '''Setup an I2C connection.
        Pins 25 and 26 are the default I2C pins (board dependend)
        '''
        self.logger.log('info', 'Setting up I2C')

        self.i2c = I2C(id, scl=scl, sda=sda, freq=freq)
        self.logger.log('info', 'Settings: {}'.format(self.i2c))
        self.logger.log('info', 'I2C setup done')

    def knownSensors(self, filename='Sensors/sensors.json'):
        '''Load id, address, type, etc. of known sensors from json file
        '''
        with open(filename, 'r') as fp:
            self.known_sensors = ujson.load(fp)

    def scanI2C(self):
        '''Scan all I2C addresses between 0x08 and 0x77 inclusive and
        return a list of those that respond.
        '''

        # the return value per I2C device is its hex address
        # Scan all I2C addresses between 0x08 and 0x77 inclusive
        addresses = self.i2c.scan()
        message = 'Addresses available on I2C: {}'.format([hex(a) for a in addresses])
        self.logger.log('info', message)

        # populate available sensors (subset or all of known sensors)
        for address in addresses:
            for sensor in self.known_sensors:
                if hex(address) in self.known_sensors[sensor]['address']:
                    sensor_type = self.known_sensors[sensor]['type']
                    message = 'Found known sensor {} ({})'.format(
                        sensor, self.known_sensors[sensor]['type'])
                    self.logger.log('info', message)
                    self.available_sensors[sensor] = self.known_sensors[sensor]

        return self.available_sensors

    def armSensors(self):
        '''Arm available sensors by attaching their drivers
        '''

        for sensor in self.available_sensors:

            if sensor == 'BME280':
                bme280s = bme280.BME280(address=0x76, i2c=self.i2c)
                self.available_sensors[sensor]['reader'] = bme280s
                self.logger.log('info', 'Sensor BME280 armed')

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
            t, p, h = reader.values
            message = 'Sensor: {}({}), Pressure {}, Temperature {}' \
                .format(sensor, address, p, t)
            # self.logger.log('info', message)

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

