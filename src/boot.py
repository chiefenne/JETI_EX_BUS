# boot.py -- run on boot-up
# this script is executed when the microcontroller boots up. It sets
# up various configuration options for the board.
# can run arbitrary Python, but best to keep it minimal


import usys as sys
from machine import Pin
import utime as time


# check platform
print('JETI BOOT - INFO: Platform:', sys.platform)
print('JETI BOOT - INFO: Operating system:', sys.version)
print('JETI BOOT - INFO: Underlying machine:', sys.implementation._machine)

# blink led 's' seconds with frequency 'hz'
def blink(led, s, hz):
    for i in range(s*hz):
        led.toggle()
        time.sleep(1/hz)

# switch off leds on TINY 2040 (they are on by default)
if 'rp2' in sys.platform:
    ledr = Pin(18, Pin.OUT)
    ledg = Pin(19, Pin.OUT)
    ledb = Pin(20, Pin.OUT)
    ledr.value(1)
    ledg.value(1)
    ledb.value(1)

    # blink red led to show we are booting
    blink(ledr, 2, 10)
     
    # mak sure red is off
    ledr.value(1)

    # switch on green led to show we are active
    ledg.value(0)

# main script to run after this one
# if not specified "main.py" will be executed
