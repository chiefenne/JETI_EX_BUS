
from machine import Pin, PWM
import utime as time
from Utils.frequency_rpm_counter import FrequencyCounter


class RPMDemo:
    """
    A class that simulates RPM readings from a frequency counter.

    Args:
    pinstr (str): A string representing the GPIO pin number.

    Attributes:
    fc (FrequencyCounter): A frequency counter object.
    rpm (int): The simulated RPM value.
    """

    def __init__(self, pinstr) -> None:
        
        # extract pin number from string
        GPIO_pin = int(pinstr[3:])

        # setup a frequency counter
        read_per_second = 10
        self.fc = FrequencyCounter(GPIO_pin, readout=read_per_second)
        
    def read_jeti(self):
        """
        Simulates RPM readings from a frequency counter.

        Returns:
        int: The simulated RPM value.
        """

        # self.rpm = self.fc.get_frequency()

        # simulate rpm
        ramp = 5
        rpm = 13000
        self.rpm = int(rpm * (time.time() % ramp) / ramp)
        
        return self.rpm

