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

    Structure of the sensors dictionary in file sensors.json:
    {
        'sensor1': {
            'device_id': 1, # unique device id
            'type': 'BME280', # type of sensor
            'address': b'\x76', # I2C address
            'data': { 
                'pressure': { 
                    'identifier': 1,
                    'description': 'Air press.',
                    'unit': 'hPa',
                    'precision': 2,
                    'data_type': 4},
                'temperature': {
                    'identifier': 2,
                    'description': 'Air temp.',
                    'unit': 'C',
                    'precision': 2,
                    'data_type': 1},
        'sensor2': {...}
    
    Telemetry identifier:
    (0: Device name)
    1: Pressure
    2: Temperature
    3: Altitude
    4: Climb rate
    5: Voltage
    6: Current
    7: Capacity
    8: RPM
    9: Fuel
    10: Speed
    13: GPS Course
    14: GPS Distance
    15: GPS Bearing
    16: GPS Time
    17: GPS Date
    18: GPS Satellites
    19: GPS Latitude
    20: GPS Longitude

    '''

    def __init__(self):
        # call constructor of JetiEx
        super().__init__()

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        self.sensors = dict()

        # upper part of the serial number (same for all sensors)
        self.productID = b'\x00a4'

        # load information of known sensors 
        self.knownSensors()

        # setup I2C connection (pins are board specific)
        # TINY2040 GPIO6, GPIO7
        sda = Pin(6)
        scl = Pin(7)
        self.setupI2C(1, scl, sda, freq=400000)

        # get all attached sensors
        self.scanI2C()
       
        # number of sensors attached
        message = 'Number of sensors attached: {}'.format(len(self.sensors))
        self.logger.log('info', message)

        # arm sensors
        self.armSensors()

        return

    def get_sensors(self):
        '''Return a list of all sensors
        '''
        return self.sensors

    def setupI2C(self, id, scl, sda, freq=100000):
        '''Setup an I2C connection.
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
                    self.sensors[sensor] = self.known_sensors[sensor]
                    message = 'Found known sensor {} ({})'.format(
                        sensor, self.known_sensors[sensor]['type'])
                    self.logger.log('info', message)

        return

    def armSensors(self):
        '''Arm available sensors by attaching their drivers
        '''

        for sensor in self.sensors:

            if sensor == 'BME280':
                bme280s = bme280.BME280(address=0x76, i2c=self.i2c)
                self.sensors[sensor]['reader'] = bme280s
                self.logger.log('info', 'Sensor BME280 armed')

            if sensor == 'MS5611':
                ms5611 = MS5611.MS5611(bus=self.i2c)
                self.sensors[sensor]['reader'] = ms5611

    def read(self, sensor):
        '''Read data from all sensors.

        The data are read in different ways, depending on the sensor driver.

        '''

        # BME280 pressure sensor
        if 'BME280' in sensor:
            address = self.sensors[sensor]['address']
            reader = self.sensors[sensor]['reader']
            t, p, h = reader.values
            self.sensors[sensor]['temperature'] = t
            self.sensors[sensor]['pressure'] = p
            self.sensors[sensor]['humidity'] = h
            message = 'Sensor {}: Pressure {:.1f} (Pa), Temperature {:.1f} (C)'.format(sensor, p, t)
            self.logger.log('info', message)
        # MS5611 pressure sensor
        if 'MS5611' in sensor:
            address = self.sensors[sensor]['address']
            reader = self.sensors[sensor]['reader']
            reader.read()
            t = reader.temperature
            p = reader.pressure
            self.sensors[sensor]['temperature'] = t
            self.sensors[sensor]['pressure'] = p
            
            message = 'Sensor {}: Pressure {:.1f} (Pa), Temperature {:.1f} (C)'.format(sensor, p, t)
            self.logger.log('info', message)

        return

    def readAll(self):
        '''Read data from all sensors.

        The data are read in different ways, depending on the sensor driver.

        '''
        for sensor in self.sensors:
            self.read(sensor)

        return
