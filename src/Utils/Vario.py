'''Variometer function for the JETI EX protocol.'''


import utime as time
import micropython


class VARIO:
   
    def __init__(self, sensor, deadzone=0.05, smoothing=0.9, filter='alpha_beta'):
        self.sensor = sensor
        self.last_altitude = 0
        self.last_climbrate = 0
        self.deadzone = deadzone
        self.smoothing = smoothing
        self.vario_filter = vario_filter
        self.vario_time_old = time.ticks_ms()

    @micropython.native
    def variometer(self, altitude):
        '''Calculate the variometer value from current altitude.'''

        # calculate delta's for gradient
        # use ticks_diff to produce correct result (when timer overflows)
        self.vario_time = time.ticks_ms()
        dt = time.ticks_diff(self.vario_time, self.vario_time_old) / 1000.0
        dz = altitude - self.last_altitude

        # calculate the climbrate
        climbrate_raw = dz / (dt + 1.e-9)

        # deadzone filtering
        deadzone = self.deadzone # cache variable to speed up
        if climbrate_raw > deadzone:
            climbrate_raw -= deadzone
        elif climbrate_raw < -deadzone:
            climbrate_raw += deadzone
        else:
            climbrate_raw = 0.0

        if filter == 'exponential':
            # smoothing filter for the climb rate
            climbrate = climbrate_raw + \
                self.smoothing * (self.last_climbrate - climbrate_raw)
        elif filter == 'alpha_beta':
            # alpha-beta filter for the climb rate
            climbrate = self.vario_filter.update(climbrate_raw)

        # store data for next iteration
        self.vario_time_old = self.vario_time
        self.last_altitude = altitude
        self.last_climbrate = climbrate

        return climbrate
