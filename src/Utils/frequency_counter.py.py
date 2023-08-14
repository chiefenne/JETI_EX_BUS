
from machine import Pin, Timer


class FrequencyCounter:
    def __init__(self, pin_num, readout=100):
        '''Read frequency from a GPIO pin
        
        Args:
            pin_num (int): Pin number
            readout (int, optional): Frequency readout interval in ms.
        
        '''
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        self.timer = Timer()
        self.timer.init(freq=readout,
                        mode=Timer.PERIODIC,
                        callback=self.timer_callback)
        self.counter = 0

        # Setup interrupt for rising edges
        self.pin.irq(trigger=Pin.IRQ_RISING, handler=self.irq_handler)

    def irq_handler(self, pin):
        self.counter += 1


    def timer_callback(self, timer):
        # frequency = counts / (timer period in ms) / 1000
        self.frequency = self.counter / timer.period() / 1000
        self.counter = 0
