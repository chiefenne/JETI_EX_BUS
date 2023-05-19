'''

Debug the Jeti serial connection

'''

from machine import Pin, UART

from Jeti.Serial_UART import Serial
from Utils.Logger import Logger


# setup a logger for the REPL
logger = Logger(prestring='JETI MAIN')