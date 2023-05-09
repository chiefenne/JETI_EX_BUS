# boot.py -- run on boot-up
# this script is executed when the pyboard boots up. It sets
# up various configuration options for the pyboard.
# can run arbitrary Python, but best to keep it minimal

# IMPORTANT:
# When the pyboard boots up, it needs to choose a filesystem to boot from.
# If there is no SD card, then it uses the internal filesystem /flash as the boot filesystem,
# otherwise, it uses the SD card /sd.
# After the boot, the current directory is set to one of the directories above.
# If needed, you can prevent the use of the SD card by creating an empty file called /flash/SKIPSD.
# If this file exists when the pyboard boots up then the SD card will be skipped and
# the pyboard will always boot from the internal filesystem
# (in this case the SD card won’t be mounted but you can still mount and
# use it later in your program using os.mount).

import usys as sys
from machine import Pin
import utime as time

# check platform
print('INFO (boot.py): Platform          --> ', sys.platform)
print('INFO (boot.py): Operating system  --> ', sys.version)

# switch off leds on TINY 2040 (they are on by default)
if 'rp2' in sys.platform:
    ledr = Pin(18, Pin.OUT)
    ledg = Pin(19, Pin.OUT)
    ledb = Pin(20, Pin.OUT)
    ledr.value(1)
    ledg.value(1)
    ledb.value(1)

    # blink red led s seconds with hz Hz
    def blink(led, s, hz):
        for i in range(s*hz):
            led.toggle()
            time.sleep(1/hz)
        
        # mak sure red is off
        ledr.value(1)

    # blink red led to show we are booting
    blink(ledr, 1, 10)

    # switch on green led to show we are active
    ledg.value(0)

# main script to run after this one
# if not specified "main.py" will be executed
