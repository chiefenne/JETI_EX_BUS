

from machine import Pin
import utime


class Tachometer:

    def __init__(self, pin) -> None:
        self.counter = 0
        self.tachometer_pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self.tachometer_pin.irq(trigger=Pin.IRQ_RISING,
                                handler=self.tachometer)

    # interrupt handler function
    def tachometer(self, pin):
        '''Increment the counter when the tachometer pin is triggered.
        
        Args:
            pin (Pin): The pin that triggered the interrupt.
        '''
        self.counter += 1

    def get_rpm(self):
        revolutions_per_sampling_time = self.counter
        revolutions_per_sec = revolutions_per_sampling_time / SAMPLING_TIME
        revolutions_per_minute = revolutions_per_sec * 60

        print("RPM : ", revolutions_per_minute)
        # reset the counter to zero
        counter = 0
