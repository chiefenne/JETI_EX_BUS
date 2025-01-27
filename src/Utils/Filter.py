import micropython


class SignalFilter:
    def __init__(self, filter_type='exponential'):
        self.filter_type = filter_type

    @micropython.native
    def exponential_filter(self, value, smoothing_factor):
        """
        Apply an exponential filter to the provided value.

        This method updates an internal stored value by applying a smoothing factor
        to gradually reduce the difference between the new value and the stored value.

        Parameters:
            value (int or float): The new measurement or target value.
            smoothing_factor (float): A number in the range [0, 1] that determines
                how much of the old value to keep. A higher value means more smoothing.

        Returns:
            float: The updated filtered value.
        """
        self.value = value + smoothing_factor * (self.value - value)
        return self.value

    @micropython.native
    def double_exponential_filter_native_typed(self, altitude: float,
                                            old_altitude_1: float,
                                            old_altitude_2: float,
                                            old_climb_rate: float,
                                            tau_1: float, tau_2: float, dyn_alpha_divisor: float,
                                            dt_us: float) -> tuple[float, float, float]:
        """Applies a double exponential filter using @native with type hints."""

        alfa_1: float = dt_us / (tau_1 + dt_us)
        alfa_2: float = dt_us / (tau_2 + dt_us)

        smoothed_altitude_1: float = old_altitude_1 - alfa_1 * (old_altitude_1 - altitude)
        smoothed_altitude_2: float = old_altitude_2 - alfa_2 * (old_altitude_2 - altitude)

        gain: float = 1_000_000.0 / (tau_2 - tau_1 + 1.0e-9)
        climb_rate: float = (smoothed_altitude_1 - smoothed_altitude_2) * gain

        dyn_alpha: float = abs((old_climb_rate - climb_rate) / dyn_alpha_divisor)
        dyn_alpha = min(dyn_alpha, 1.0)

        smoothed_climb_rate: float = old_climb_rate - dyn_alpha * (old_climb_rate - climb_rate)

        return smoothed_altitude_1, smoothed_altitude_2, smoothed_climb_rate

    @micropython.native
    def alpha_beta_filter(self,
                          measurement,
                          alpha,
                          beta,
                          initial_value=0,
                          initial_velocity=0,
                          delta_t=1):

        estimate = initial_value
        self.velocity = initial_velocity

        estimate += self.velocity * delta_t
        error = measurement - estimate
        estimate += alpha * error
        self.velocity += (beta / delta_t) * error
        return estimate

    @micropython.native
    def alpha_beta_filter_integer(self,
                                  measurement,
                                  alpha,
                                  beta,
                                  scale=1000,
                                  initial_value=0,
                                  initial_velocity=0,
                                  delta_t=1):

        self.beta = beta       # integer-based scaling factor
        self.scale = scale
        self.estimate = initial_value
        self.velocity = initial_velocity
        self.delta_t = delta_t

        self.estimate += self.velocity * self.delta_t
        error = measurement - self.estimate
        self.estimate += (alpha * error) // self.scale
        self.velocity += (self.beta * error) // (self.scale * self.delta_t)
        return self.estimate

