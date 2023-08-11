'''
Handle JetiBox
'''

from Utils.logger import Logger

class JetiBox:

    def __init__(self):


        # setup a logger for the REPL
        self.logger = Logger(prestring='JETIBOX')

    def getKey(self):
        '''Get the key pressed on the JetiBox.'''

        # wait for a key to be pressed
        while True:
            key = self.jetiBox.key()
            if key != 0:
                break

        return key
