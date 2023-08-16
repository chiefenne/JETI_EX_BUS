
import machine
import time
from machine import Pin, Timer
from rp2 import asm_pio, PIO, StateMachine


class FrequencyCounter:
    def __init__(self, GPIO_PIN, readout=100):
        '''Read frequency from a GPIO pin
        
        Args:
            GPIO_PIN (int): Pin number
            readout (int, optional): Frequency readout interval in ms.
        
        '''
        self.pin = Pin(GPIO_PIN, Pin.IN, Pin.PULL_DOWN)
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


class RPMCounter:
    def __init__(self, GPIO_PIN, reading_freq_hz):
        self.pin = machine.Pin(GPIO_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.pin.irq(trigger=machine.Pin.IRQ_RISING, handler=self.irq_handler)

        self.reading_freq_hz = reading_freq_hz
        self.reading_interval = int(
            1000000 / self.reading_freq_hz)  # in microseconds
        # set threshold to 80% of reading interval
        self.threshold = self.reading_interval * 0.8

        self.last_time = time.ticks_us()
        self.rpm = 0
        self.counter = 0
        self.method = 'time_between'  # start with time between pulses method

    def irq_handler(self, pin):
        if self.method == 'time_between':
            current_time = time.ticks_us()
            delta = time.ticks_diff(current_time, self.last_time)

            if delta and delta < self.threshold:
                self.rpm = 60000000 / (delta * self.reading_freq_hz)
            else:
                self.method = 'fixed_interval'
                self.counter = 0
                self.start_time = current_time

            self.last_time = current_time

        elif self.method == 'fixed_interval':
            self.counter += 1
            delta = time.ticks_diff(time.ticks_us(), self.start_time)

            if delta >= self.reading_interval:
                self.rpm = self.counter * 60 * self.reading_freq_hz

                if self.counter > 2:  # If we get more than 2 pulses during the interval, switch back
                    self.method = 'time_between'
                self.counter = 0
                self.start_time = time.ticks_us()

    def get_rpm(self):
        return self.rpm


class RPMCounter2:
    '''This is a class for measuring RPM using PIO of the Raspberry Pi RP2040.

    Source: https://forums.raspberrypi.com/viewtopic.php?t=316491#p1893864
    
    '''

    # RP2040 has 8 statemachines, so limit the number of instances to 8
    instances = -1

    def __init__(self, GPIO_PIN, reading_freq_hz):

        # Check if we have any free PIO statemachines
        RPMCounter2.instances += 1
        if RPMCounter2.instances >= 8:
            raise Exception("No free statemachines")

        counter_pin = Pin(GPIO_PIN, Pin.IN, Pin.PULL_DOWN)
        self.sm = StateMachine(RPMCounter2.instances, self.PulseIn,
                          in_base=counter_pin, jmp_pin=counter_pin)
        self.sm.active(1)

        # 
        run()

    @asm_pio()
    def PulseIn():
        set(x, 0)           # X = 0;
        wait(0, pin, 0)     # Do {} While ( pin == 1 );
        wait(1, pin, 0)     # Do {} While ( pin == 0 );
        label("loop")       # Do
        jmp(x_dec, "next")  #   X--;
        label("next")
        jmp(pin, "loop")    # While ( pin == 1 );
        mov(isr, x)         # Push(X);
        push(isr, block)

    def run(self):
        while True:
            # Note the count is decremented in the PIO routine so it will be a
            # negative value. We need to make it a positive value.
            cnt = (1 << 32) - self.sm.get()
            tms = cnt / 62500
            rps = 1_000 / tms
            rpm = rps * 60
            time.sleep(1)