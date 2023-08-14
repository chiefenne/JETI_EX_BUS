
import machine


class FrequencyCounter:
    def __init__(self, pin_num):
        self.pin = machine.Pin(pin_num, machine.Pin.IN)
        self.timer = machine.Timer(-1)
        self.counter = 0

        # Setup interrupt for rising edges
        self.pin.irq(trigger=machine.Pin.IRQ_RISING, handler=self.irq_handler)

    def irq_handler(self, pin):
        self.counter += 1

    def start(self, duration_ms=1000):
        self.counter = 0
        self.timer.init(period=duration_ms,
                        mode=machine.Timer.PERIODIC,
                        callback=self.timer_callback)

    def timer_callback(self, timer):
        self.counter = 0
        self.frequency = self.counter / timer.period()
