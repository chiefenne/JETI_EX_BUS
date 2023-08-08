'''
Alpha-Beta filter for smoothing noisy sensor data.
'''

import micropython


class AlphaBetaFilter:
    def __init__(self, alpha, beta, initial_value=0, initial_velocity=0, delta_t=1):
        self.alpha = alpha
        self.beta = beta
        self.estimate = initial_value
        self.velocity = initial_velocity
        self.delta_t = delta_t

    @micropython.native
    def update(self, measurement):
        # Predict
        self.estimate += self.velocity * self.delta_t

        # Update based on measurement
        error = measurement - self.estimate
        self.estimate += self.alpha * error
        self.velocity += (self.beta / self.delta_t) * error

        return self.estimate
