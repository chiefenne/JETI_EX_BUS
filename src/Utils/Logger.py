'''Simple logger for information and debugging

Used when connected to the microcontroller (e.g. Pyboard) and monitoring the
code via the REPL

'''


class Logger:

    def __init__(self, prestring='JETI'):
        self.default_prestring = prestring
        self.prestring = prestring

    def log(self, msg_type, message):
        # define different debug levels for print statements to the REPL
        header = {'info': self.prestring + ' - INFO: ',
                'debug': self.prestring + ' - DEBUG: ',
                'warning': self.prestring + ' - WARNING: ',
                'error': self.prestring + ' - ERROR: '}
        
        print(header[msg_type] + message)

    def empty(self):
        print(' ')

    def setPreString(self, prestring):
        self.prestring = prestring

    def resetPreString(self):
        self.prestring = self.default_prestring
