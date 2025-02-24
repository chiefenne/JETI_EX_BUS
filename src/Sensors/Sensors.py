'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

Author: Dipl.-Ing. A. Ennemoser
Date: 04-2021

'''

import json

from Utils.Logger import Logger


class Sensors:
    '''This class represents all sensors attached via I2C.

    Sensors are connected with their 'default' I2C address. The addresses
    are stored in a dictionary. The dictionary key is the name of the sensor
    and the value is the I2C address.

    '''

    def __init__(self, addresses, i2c):

        # sensor data (ordered by I2C address)
        with open('Sensors/sensors.json') as f:
            self.sensor_data = json.load(f)

        # telemetry meta data (16 fields per device including the device name)
        # this means 15 fields are available for sensors
        # a second device can be used for another 15 sensors
        # another deviceID has to be set in this case
        with open('Sensors/telemetry.json') as f:
            self.telemetry_metadata = json.load(f)

        self.sensors = list()
        self.addresses = addresses
        self.i2c = i2c

        # upper part of the serial number (same for all sensors)
        # LSB first, MSB last
        self.productID = b'\x00' + b'\xa4'

        # lower part of the serial number (unique for each sensor)
        # i.e., the microcontroller is here the sensor
        # LSB first, MSB last
        # for more than 15 sensors a second deviceID has to be set
        self.deviceID = b'\x00' + b'\x01'

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI SENSOR')

        # activate the sensors
        self.arm()

        # number of sensors attached
        message = 'Number of sensors attached: {}'.format(len(self.sensors))
        self.logger.log('info', message)

        return

    def arm(self):
        '''Arm the I2C sensors.'''

        for address in self.addresses:

            # convert int address to hex (returns a string)
            addr = hex(address)

            # import the module for the I2C sensor dynamically from sensors.json
            sensor_defs = __import__('Sensors/' + self.sensor_data[addr]['module'])
            sensor_class = getattr(sensor_defs, self.sensor_data[addr]['class'])
            sensor = sensor_class(self.i2c, address)

            sensor.address = address
            sensor.name = self.sensor_data[addr]['name']
            sensor.manufacturer = self.sensor_data[addr]['manufacturer']
            sensor.description = self.sensor_data[addr]['description']
            sensor.category = self.sensor_data[addr]['category']
            sensor.labels = self.sensor_data[addr]['labels']

            self.sensors.append(sensor)

            message = f"Found sensor: {sensor.name}, Category: {sensor.category}"
            self.logger.log('info', message)

        return

    def get_sensors(self):
        '''Return a list of all sensors
        '''
        return self.sensors
