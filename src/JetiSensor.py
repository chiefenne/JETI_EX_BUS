'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''

import machine


class JetiSensor(JetiEx):
    '''This class represents a sensor.
    '''

    def __init__(self):
        super().__init__()

        self.sensors = None
