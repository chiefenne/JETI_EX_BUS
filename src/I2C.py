'''Class for connecting to the I2C bus and collecting attached hardware'''

# modules starting with 'u' are Python standard libraries which
# are stripped down in MicroPython to be efficient on microcontrollers
import usys as sys
from machine import I2C, Pin
import ujson


class Connect:
    '''This class represents all sensors attached via I2C
    '''

    def __init__(self):

        self.bus = None
        self.available_sensors = dict()

        # load information of known sensors 
        self.knownSensors()

        # setup I2C bus
        self.bus = I2C(scl=Pin('X9'), sda=Pin('X10'), freq=400000)

        # get attached devices
        self.scanI2C()

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
