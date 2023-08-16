
from machine import Pin, PWM

from frequency_rpm_counter import FrequencyCounter


class RPMDemo:

    def __init__(self, GPIO_pin) -> None:
         
        # Set up a PWM
        pwm_pin = PWM(Pin(GPIO_pin))
        pwm_pin.freq(1000)  # Set frequency to 1kHz
        pwm_pin.duty_u16(32768)  # 50% duty cycle

        # Configure the same pin as input (just for testing)
        read_per_second = 10
        self.freq_counter = FrequencyCounter(
            GPIO_pin, readout=read_per_second)

    def read_jeti(self):

        self.rpm = self.freq_counter.counter

        return self.rpm

