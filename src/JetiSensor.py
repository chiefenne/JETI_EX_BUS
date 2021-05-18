'''Base class for all sensors.

Each sensor needs to be derived from this class.

'''


class Sensor:
    '''Base class for all sensors.
    '''

    def __init__(self):
        pass

    def read(self):
        '''This method neeeds to be implemented in subclasses
        '''
        pass
