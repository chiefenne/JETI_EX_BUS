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
    # set nominal CPU frequency (so that printout is correct)
    freq(125_000_000)
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

def blink(led, seconds, hz):
    """
    Blink LED for 'seconds' and 'hz' frequency.
    """
    if hz <= 0 or seconds <= 0:
        return
    interval = 1 / hz
    for _ in range(int(seconds * hz)):
        led.value(not led.value())
        time.sleep(interval)
    led.value(1)  # ensure LED is off

# attempt to switch off and blink LEDs; pin assignments may differ across rp2 boards
if 'rp2' in sys.platform:
    # SEEED XIA RP2040 RGB pins; NeoPixel LED is 11 (power) and 12 (data)
    rp2_led_pins = {'r': 17, 'g': 16, 'b': 25}
    try:
        ledr = Pin(rp2_led_pins['r'], Pin.OUT)
        ledg = Pin(rp2_led_pins['g'], Pin.OUT)
        ledb = Pin(rp2_led_pins['b'], Pin.OUT)
        for led in (ledr, ledg, ledb):
            led.value(1)
        blink(ledr, 2, 10)
        blink(ledg, 4, 5)
        ledg.value(0)  # indicate active
    except:
        print("JETI BOOT - ERROR: LED setup failed on RP2040")

elif 'esp32' in sys.platform:
    try:
        # default built-in LED on some boards is GPIO2, others vary
        led = Pin(21, Pin.OUT)
        blink(led, 5, 4)
        led.value(0)  # indicate active
    except:
        print("JETI BOOT - ERROR: LED setup failed on ESP32")

# main script to run after this one
# if not specified "main.py" will be executed
