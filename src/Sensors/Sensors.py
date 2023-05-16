'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

from Sensors.sensor_BME280 import BME280_Sensor
from Sensors.sensor_MS5611 import MS5611_Sensor
from Utils.Logger import Logger


class Sensors:
    '''This class represents all sensors attached via I2C.
    
    Sensors are connected with their 'default' I2C address. The addresses
    are stored in a dictionary. The dictionary key is the name of the sensor
    and the value is the I2C address.

    '''

    def __init__(self, addresses, i2c):
        
        # telemetry identifiers
        self.ID_VOLTAGE = 0
        self.ID_ALTITUDE = 1
        self.ID_CLIMB = 2
        self.ID_PRESSURE = 3
        self.ID_TEMP = 4
        self.ID_FUEL = 5
        self.ID_RPM = 6
        self.ID_GPSLAT = 7
        self.ID_GPSLON = 8
        self.ID_DISTANCE = 9
        self.ID_HEADING = 10
        self.ID_SATELLITES = 11

        # sensor meta data for the Jeti Ex telemetry
        self.meta = {
            'ID_VOLTAGE': {
                'description': 'Voltage',
                'unit': 'V',
                'data_type': 1, # int14_t
                'precision': 1
            },
            'ID_ALTITUDE': {
                'description': 'Altitude',
                'unit': 'm',
                'data_type': 1, # int14_t
                'precision': 0
            },
            'ID_CLIMB': {
                'description': 'Climb',
                'unit': 'm/s',
                'data_type': 1, # int14_t
                'precision': 2
            },
            'ID_PRESSURE': {
                'description': 'Pressure',
                'unit': 'hPa',
                'data_type': 4, # int22_t
                'precision': 1
            },
            'ID_TEMP': {
                'description': 'Temperature',
                'unit': 'C',
                'data_type': 1, # int14_t
                'precision': 1
            },
            'ID_CAPACITY': {
                'description': 'Capacity',
                'unit': '%',
                'data_type': 1, # int14_t
                'precision': 0
            },
            'ID_RPM': {
                'description': 'RPM',
                'unit': '1/min',
                'data_type': 1, # int14_t
                'precision': 1
            },
            'ID_GPSLAT': {
                'description': 'Latitude',
                'unit': ' ',
                'data_type': 9, # GPS
                'precision': 0
            },
            'ID_GPSLON': {
                'description': 'Longitude',
                'unit': ' ',
                'data_type': 9, # GPS
                'precision': 0
            },
            'ID_DISTANCE': {
                'description': 'Distance',
                'unit': 'm',
                'data_type': 1, # int14_t
                'precision': 0
            },
            'ID_HEADING': {
                'description': 'Heading',
                'unit': '-',
                'data_type': 1, # int14_t
                'precision': 0
            },
            'ID_SATELLITES': {
                'description': 'Satellites',
                'unit': '_',
                'data_type': 1, # int14_t
                'precision': 0
            }
        }

        self.sensors = list()
        self.addresses = addresses
        self.i2c = i2c

        # upper part of the serial number (same for all sensors)
        self.productID = b'\x00' + b'\xa4'

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        # activate the sensors
        self.arm()

        return

    def arm(self):
        '''Arm the sensors
        '''

        # arm the sensors
        bme280 = BME280_Sensor(address=0x76, i2c=self.i2c)
        bme280.arm()

        ms5611 = MS5611_Sensor(address=0x77, i2c=self.i2c, elevation=0)
        ms5611.arm()

        # add the sensors to the list of sensors
        self.sensors.append(bme280)
        self.sensors.append(ms5611)

        # number of sensors attached
        message = 'Number of sensors attached: {}'.format(len(self.sensors))
        self.logger.log('info', message)

        return

    def get_sensors(self):
        '''Return a list of all sensors
        '''
        return self.sensors
