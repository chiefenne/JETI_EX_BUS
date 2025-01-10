# boot.py -- run on boot-up
# this script is executed when the microcontroller boots up. It sets
# up various configuration options for the board.
# can run arbitrary Python, but best to keep it minimal


import usys as sys
from machine import Pin, freq
import utime as time


# check platform
print('JETI BOOT - INFO: Platform:', sys.platform)
print('JETI BOOT - INFO: Operating system:', sys.version)
print('JETI BOOT - INFO: Underlying machine:', sys.implementation._machine)

overclock = False

if 'rp2' in sys.platform:
    overclock = True
elif 'esp32' in sys.platform:
    overclock = True
elif 'samd' in sys.platform:
    pass
else:
    print(f'JETI BOOT - INFO: Unknown platform: {sys.platform}')

print(f'JETI BOOT - INFO: CPU frequency (MHz): {freq() / 1_000_000}')

if overclock:
    if 'rp2' in sys.platform or 'esp32' in sys.platform:
        freq(240_000_000)
        print(f'JETI BOOT - INFO: CPU overclocked frequency (MHz): {freq() / 1_000_000}')

# blink led 's' seconds with frequency 'hz'
def blink(led, s, hz):
    for i in range(s*hz):
        led.value(not led.value()) # toggle led
        time.sleep(1/hz)
     
    # mak sure led is off
    led.value(1)

# switch off leds on TINY 2040 (they are on by default)
if 'rp2' in sys.platform:
    try:
        ledr = Pin(18, Pin.OUT)
        ledg = Pin(19, Pin.OUT)
        ledb = Pin(20, Pin.OUT)
        ledr.value(1)
        ledg.value(1)
        ledb.value(1)

        # blink led to show we are booting
        blink(ledr, 3, 10)

        # switch on green led to show we are active
        ledg.value(0)
    except:
        print('JETI BOOT - ERROR: No LED found on RP2040 board')

if 'esp32' in sys.platform:

    try:
        # ESP32 has a built-in led at pin
        led = Pin(21, Pin.OUT)

        # blink  led to show we are booting
        blink(led, 5, 4)

        # switch on led to show we are active
        led.value(0)
    except:
        print('JETI BOOT - ERROR: No LED found on ESP32 board')

# main script to run after this one
# if not specified "main.py" will be executed
