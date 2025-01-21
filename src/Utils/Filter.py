import micropython


class SignalFilter:
    def __init__(self, filter_type='exponential'):
        self.filter_type = filter_type

    @micropython.native
    def exponential_filter(self, value, smoothing_factor):
        self.value = value + int(smoothing_factor * (self.last_climbrate - value))
        return self.value

    @micropython.native

    def double_exponential_filter(self,
                                    input_value,
                                    prev_output,
                                    ref_init,
                                    ref_curr,
                                    alpha,
                                    factor):
            """Applies a double exponential filter with dynamic smoothing to an input value.

            Args:
                input_value (float): The raw, noisy input value to be filtered.
                prev_output (float): The previous smoothed output value.
                ref_init (float): A slower-moving reference value.
                ref_curr (float): A faster-moving reference value.
                alpha (float): The smoothing factor (0 to 1).
                factor (float): A factor to calculate the base output value.

            Returns:
                tuple[float, float, float]: The updated ref_init, ref_curr, and the new filtered output value.
            """

            ref_init_new = ref_init - alpha * (ref_init - input_value)
            ref_curr_new = ref_curr - alpha * (ref_curr - input_value)

            base_output = (ref_init_new - ref_curr_new) * factor

            dyn_alpha = abs((prev_output - base_output) / 0.4)
            if dyn_alpha >= 1:
                dyn_alpha = 1
            new_output = prev_output - dyn_alpha * (prev_output - base_output)

            return ref_init_new, ref_curr_new, new_output

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

