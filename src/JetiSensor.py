'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
from machine import I2C, Pin
import ujson

# check if we are on a Pyboard (main development platform for this code)
pyboard = False
if 'pyboard' in sys.platform:
    import pyb
    pyboard = True


import bme280_float as bme280
import MS5611
import Logger


class I2C_Sensors:
    '''This class represents all sensors attached via I2C
    '''

    def __init__(self):
        # call constructor of JetiEx
        super().__init__()

        # setup a logger for the REPL
        self.logger = Logger.Logger()

        self.available_sensors = dict()

        # load information of known sensors 
        self.knownSensors(filename='sensors.json')

        # setup I2C connection to sensors
        if pyboard:
            self.setupI2C(1, 'X9', 'X10')
        else:
            self.setupI2C(1, 25, 26)

        # get all attached sensors
        self.scanI2C()

        # arm sensors
        self.armSensors()

    def setupI2C(self, id, scl, sda, freq=400000):
        '''Setup an I2C connection.
        Pins 25 and 26 are the default I2C pins (board dependend)
        '''
        # self.i2c = I2C(Pin(scl), Pin(sda))
        self.logger.log('info', 'Setting up I2C')
        self.i2c = I2C(scl=Pin('X9'), sda=Pin('X10'))
        self.logger.log('info', 'I2C setup done')

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
        # Scan all I2C addresses between 0x08 and 0x77 inclusive
        addresses = self.i2c.scan()
        print('Addresses on I2C:', addresses, [hex(a) for a in addresses])

        # populate available sensors (subset or all of known sensors)
        for address in addresses:
            for sensor in self.known_sensors:
                if hex(address) in self.known_sensors[sensor]['address']:
                    sensor_type = self.known_sensors[sensor]['type']
                    print('Found sensor of type:', self.known_sensors[sensor]['type'])
                    self.available_sensors[sensor] = {'type': sensor_type,
                                               'address': address}

        return self.available_sensors

    def armSensors(self):
        '''Arm available sensors by attaching their drivers
        '''

        print('Arming sensors from', self.available_sensors)
        for sensor in self.available_sensors:

            print('Arming sensor:', sensor)
            
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
            p, t, h = reader.values
            message = 'Sensor: {}, Address {}, Pressure {}, Temperature {}, humidity {}' \
                .format(sensor, address, p, t, h)
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

