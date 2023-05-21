'''

Debug the Jeti serial connection

'''

from machine import Pin, UART

from Jeti.Serial_UART import Serial
from Utils.Logger import Logger


# setup a logger for the REPL
logger = Logger(prestring='JETI SERIAL')

# Serial connection bewtween Jeti receiver and microcontroller
# defaults: baudrate=125000, 8-N-1
s = Serial(port=0)
serial = s.connect()

# read 1 second of the serial stream to a text file for debugging purposes
DEBUG = True
if DEBUG:
    logger.log('info', 'DEBUG mode is ON')
    logger.log('info', 'Writing EX_Bus_stream.txt')
    with open('EX_Bus_stream.txt', 'w') as f:
        for i in range(1000):
            f.write(str(serial.read(1)))
    logger.log('info', 'Writing EX_Bus_stream.txt finished')
else:
    logger.log('info', 'DEBUG mode is OFF')
    logger.log('info', 'Writing EX_Bus_stream.txt is disabled')

# close the serial connection
s.disconnect()

