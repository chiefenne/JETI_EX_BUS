'''Class for handling a sensor

For example the sensor can be a pressure sensor (e.g. BME280) which in turn
is used to make up a vario.

'''


class JetiSensor(JetiEx):
    '''

    Args:
        JetiEx (class): Jeti EX protocol implementation
    '''

    def __init__(self):
        super().__init__()