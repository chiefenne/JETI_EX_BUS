'''Function to record a part of the serial stream
'''

import uos
import utime
from binascii import hexlify


def saveStream(serial, logger, filename='EX_Bus_stream.txt', duration=1000):
    '''Write a part of the serial stream to a text file on the SD card 
    for debugging purposes.

    The "memoryview" hack credits go to:
    https://forum.micropython.org/viewtopic.php?t=1259#p8002

    NOTE: Do not use this function during normal operation.
            When debugging, use this call by 

    NOTE: Writing to the SD card sometimes doesn't work.
            Do a hard reset when this function is active.
            After the hard reset the file 'EX_Bus_stream.txt' should exist.
    '''

    start = utime.ticks_ms()
    time = 0.

    f = open(filename, 'w')

    while time < duration:

        buf = bytearray(5000)  
        mv = memoryview(buf)
        idx = 0

        while idx < len(buf):
            if serial.any() > 0:
                bytes_read = serial.readinto(mv[idx:])
                # print('Got {} bytes of data'.format(bytes_read),
                #    hexlify(buf[idx:idx+bytes_read], b':'))
                idx += bytes_read

        f.write(hexlify(buf, b':') + '\n')

        time = utime.ticks_diff(utime.ticks_ms(), start)

    f.close()

    message = 'EX Bus stream recorded for {} seconds.'.format(duration/1000.)
    logger.log('debug', message)
