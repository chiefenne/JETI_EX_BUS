
import JetiSensor


class VarioSensor(JetiSensor):
    '''Vario functionality via pressure sensor.

    Args:
        JetiSensor (class): Base class for all sensors
    '''

    def __init__(self):
        super().__init__()
    
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
