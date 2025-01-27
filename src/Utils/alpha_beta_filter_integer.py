'''
Alpha-Beta filter for smoothing noisy sensor data.
'''

import micropython


class AlphaBetaFilter:
    def __init__(self, alpha, beta, scale=1000, initial_value=0, initial_velocity=0, delta_t=1):
        self.alpha = alpha     # integer-based scaling factor
        self.beta = beta       # integer-based scaling factor
        self.scale = scale
        self.estimate = initial_value
        self.velocity = initial_velocity
        self.delta_t = delta_t

    @micropython.native
    def update(self, measurement):
        self.estimate += self.velocity * self.delta_t
        error = measurement - self.estimate
        self.estimate += (self.alpha * error) // self.scale
        self.velocity += (self.beta * error) // (self.scale * self.delta_t)
        return self.estimate
