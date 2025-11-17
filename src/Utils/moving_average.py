'''Calculate the moving average of a time series using a sliding window.
'''

try:
    from collections import deque
except ImportError:
    # Fallback for environments without collections.deque
    deque = None


class MovingAverageFilter:
    def __init__(self, window_size):
        self.window_size = window_size
        # Use deque for O(1) popleft operations instead of O(n) pop(0)
        if deque is not None:
            self.values = deque(maxlen=100)
            self.times = deque(maxlen=100)
        else:
            self.values = []
            self.times = []
        self.use_deque = deque is not None

    def update(self, value, time):
        self.values.append(value)
        self.times.append(time)

        # Remove values outside the window
        if self.use_deque:
            # O(1) popleft operation with deque
            while len(self.times) > 0 and self.times[-1] - self.times[0] > self.window_size:
                self.values.popleft()
                self.times.popleft()
        else:
            # Fallback to list with O(n) pop(0)
            while len(self.times) > 0 and self.times[-1] - self.times[0] > self.window_size:
                self.values.pop(0)
                self.times.pop(0)
            
            # keep number of values limited for lists
            if len(self.values) > 100:
                self.values.pop(0)
                self.times.pop(0)

        # Compute the moving average
        average = sum(self.values) / len(self.values)

        return average