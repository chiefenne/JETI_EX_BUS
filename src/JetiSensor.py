'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

from machine import I2C, Pin
import ujson


class Sensors:
    '''This class represents all sensors attached via I2C
    '''

    def __init__(self):
        # call constructor of JetiEx
        super().__init__()

        self.sensors = dict()
        # load information of known sensors 
        self.knownSensors(filename='sensors.json')

        # setup I2C connection to sensors
        self.setupI2C(scl=25, sda=26)

        # get all attached sensors
        self.scanI2C()

    def setupI2C(self, id=1, scl=25, sda=26, freq=400000):
        '''Setup an I2C connection.
        Pins 25 and 26 are the default I2C pins (board dependend)
        '''
        self.i2c = I2C(id, scl=Pin(scl), sda=Pin(sda), freq=freq)

    def knownSensors(self, filename='sensors.json'):
        '''Load id, address, type, etc. of known sensors from json file
        
        Example sensor.json file {ID: {type, address}}:
        {
            "BME280": {"type": "pressure", "address": "0x76"},
            "MS5611": {"type": "pressure", "address": "0x77"},
            "NEO-M8": {"type": "gps", "address": "0x42"}
        }
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
                if address in self.known_sensors[sensor_id]:
                    sensor_type = self.known_sensors[sensor_id][0]
                    self.sensors[sensor_id] = [address, sensor_type]

        return self.sensors
