'''Class for handling an I2C bus'''

from machine import I2C

from Utils.Logger import Logger


class I2C_bus:

    def __init__(self, id, scl=None, sda=None, freq=100000):
        '''Initialize the I2C bus.

        Parameters
        ----------
        id : int
            I2C bus id/port. Depends on the microcontroller.
        scl : Pin
            Pin object for the SCL pin.
        sda : Pin
            Pin object for the SDA pin.
        freq : int
            Frequency of the I2C bus.
        '''
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq

        # setup a logger for the REPL
        self.logger = Logger(prestring='JETI I2C')

        self.logger.log('info', 'Setting up I2C')
        self.i2c = I2C(self.id, scl=self.scl, sda=self.sda, freq=self.freq)
        self.logger.log('info', 'Settings: {}'.format(self.i2c))
        self.logger.log('info', 'I2C setup done')
       
    def scan(self):
        '''Scan the I2C bus for devices.

        The return value per I2C device is its hex address
        Scan all I2C addresses between 0x08 and 0x77 inclusive
        The corresponding sensor needs to be added in the file Sensors.py

        Returns
        -------
        list
            List of addresses of devices on the I2C bus.
        '''

        self.addresses = self.i2c.scan()

        # offer a demo sensor if no sensor is attached to the microcontroller
        if self.addresses == []:
            self.addresses = [0x99]
            self.logger.log('info', 'No sensor found. Using DEMO sensor.')

        message = 'Addresses available on I2C: {}'.format([hex(a) for a in self.addresses])
        self.logger.log('info', message)


        return self.addresses

    

