'''
'''


class MovingAverageFilter:
    def __init__(self, window_size):
        self.window_size = window_size
        self.values = []
        self.times = []

    def update(self, value, time):
        self.values.append(value)
        self.times.append(time)

        # Remove values outside the window
        while self.times[-1] - self.times[0] > self.window_size:
            self.values.pop(0)
            self.times.pop(0)

        # Compute the moving average
        average = sum(self.values) / len(self.values)

        return average