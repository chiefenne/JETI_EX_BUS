import numpy as np
import matplotlib.pyplot as plt
import random
from scipy.optimize import minimize
from scipy.optimize import Bounds

def generate_altitude_signal(duration, dt, noise_amplitude=0, add_noise=True):
    """
    Generates an artificial altitude signal simulating two cycles of climb, plateau, and descent.
    New profile: climb 2.5m in 2.5s, stay at 2.5m for 1s, sink to 0m in 0.25s and stay at 0m für 0.75s. one cycle is 4.5s. make two cycles

    Args:
        duration (float): Total duration of the signal in seconds.
        dt (float): Sampling interval in seconds.
        noise_amplitude (float): Amplitude of the random noise in meters.
        add_noise (bool): Flag to add noise to the altitude signal (default: True).

    Returns:
        tuple: A tuple containing:
          - times (list): A list of time points for the signal.
          - altitude_signal (list): A list of altitude values (including noise if add_noise is True).
          - climb_rate_signal (list): A list of the real climb rate.
    """

    times = np.arange(0, duration, dt)
    altitude_signal_ideal = [] # Ideal altitude without noise calculation
    climb_rate_signal = []
    cycle_duration = 4.5

    # Calculate the altitude based on the time
    for t in times:
        time_in_cycle = t % cycle_duration
        if time_in_cycle < 2.5:
            # climbing phase (2.5m in 2.5s)
            altitude = (2.5 / 2.5) * time_in_cycle  # 1 m/s climb rate
            climb_rate = (2.5 / 2.5)
        elif time_in_cycle < 2.5 + 1.0:
            # plateau phase at 2.5m (1s)
            altitude = 2.5
            climb_rate = 0
        elif time_in_cycle < 2.5 + 1.0 + 0.25:
            # descent phase (sink to 0m in 0.25s)
            altitude = 2.5 - (2.5 / 0.25) * (time_in_cycle - (2.5 + 1.0)) # -10 m/s sink rate
            climb_rate = -(2.5 / 0.25)
        elif time_in_cycle < 2.5 + 1.0 + 0.25 + 0.75:
            # plateau phase at 0m (0.75s)
            altitude = 0
            climb_rate = 0
        else: # this should not happen given the modulo operation, but for completeness
            altitude = 0
            climb_rate = 0

        altitude_signal_ideal.append(altitude) # Store ideal altitude
        climb_rate_signal.append(climb_rate)
        # climb_rate_signal = np.array(climb_rate_signal)

    if add_noise:
        # Add random noise to the IDEAL altitude signal
        noisy_altitude_signal = [
            altitude + random.uniform(-noise_amplitude, noise_amplitude) for altitude in altitude_signal_ideal
        ]
        return times, noisy_altitude_signal, climb_rate_signal, altitude_signal_ideal # Return noisy and ideal altitude
    else:
        return times, altitude_signal_ideal, climb_rate_signal, altitude_signal_ideal # Return ideal altitude (and also ideal as 'noisy' to keep function signature consistent)


def double_exponential_filter(altitude,
                              old_altitude_1,
                              old_altitude_2,
                              old_climb_rate,
                              tau_1, tau_2, dyn_alpha_divisor,
                              delta_t):

        alfa_1 = delta_t / (tau_1 + delta_t)
        alfa_2 = delta_t / (tau_2 + delta_t)

        smoothed_altitude_1 = old_altitude_1 - alfa_1 * (old_altitude_1 - altitude)
        smoothed_altitude_2 = old_altitude_2 - alfa_2 * (old_altitude_2 - altitude)

        # calc default gain from time constants chosen
        factor = 1 / (tau_2 - tau_1 + 1.e-9)

        climb_rate = (smoothed_altitude_1 - smoothed_altitude_2) * factor

        dyn_alpha = abs((old_climb_rate - climb_rate) / dyn_alpha_divisor)
        dyn_alpha = min(dyn_alpha, 1.0)
        smoothed_climb_rate = old_climb_rate - dyn_alpha * (old_climb_rate - climb_rate)

        return smoothed_altitude_1, smoothed_altitude_2, smoothed_climb_rate

def target_function(params, times, climb_rate_ideal, noisy_altitude):

    """Calculates a target function"""

    tau_1, tau_2, dyn_alpha_divisor = params
    delta_t = np.diff(times)
    # insert a value at the beginning to delta_t to keep the length of the arrays consistent
    delta_t = np.insert(delta_t, 0, delta_t[0])

    old_altitude_1 = noisy_altitude[0]
    old_altitude_2 = noisy_altitude[0]
    climb_rate = 0

    filtered_climb_rate = np.zeros(len(noisy_altitude))
    for i in range(len(noisy_altitude)):
       dt = delta_t[i]
       old_altitude_1, old_altitude_2, climb_rate = double_exponential_filter(noisy_altitude[i],
                                                                               old_altitude_1,
                                                                               old_altitude_2,
                                                                               climb_rate,
                                                                               tau_1, tau_2, dyn_alpha_divisor,
                                                                               dt)
       filtered_climb_rate[i] = climb_rate

    climb_rate_ideal = np.array(climb_rate_ideal) # Use climb_rate_ideal

    # Calculate the lag - now altitude lag
    lag = np.sum((filtered_climb_rate - climb_rate_ideal) ** 2) # Error between filtered and ideal climb rate

    # Calculate the derivative to find noise
    dt_time = np.diff(times)
    filtered_climb_rate_deriv = np.diff(filtered_climb_rate)
    noise = np.sum((filtered_climb_rate_deriv / dt_time) ** 2) # Error between filtered climb rate derivative and ideal climb rate derivative

    # Weighted Target Function: Lag + Noise - USER CAN ADJUST NOISE_WEIGHT
    NOISE_WEIGHT = 0.009 # User-adjustable weight for noise term - Start with 0.1, adjust as needed
    target =  lag + (NOISE_WEIGHT * noise) # Weighted sum of lag and noise

    return target


if __name__ == "__main__":

    duration = 9  # Total duration: 2 cycles * 4.5s = 9 seconds
    dt = 0.012     # Sample interval: 0.02 seconds (50 Hz)
    noise_amplitude = 0.1  # Noise amplitude

    times, noisy_altitude, _, ideal_altitude = generate_altitude_signal(
        duration, dt,
        noise_amplitude=noise_amplitude,
        add_noise=True
    )  # Generate noisy altitude

    times_ideal_altitude, _, climb_rate_ideal, ideal_altitude = generate_altitude_signal(
        duration, dt,
        noise_amplitude=0,
        add_noise=False
    )  # Generate ideal altitude (no noise)

    # Initial guesses for parameters tau_1, tau_2
    initial_params = [0.1, 0.18, 1.0]

    # Parameter bounds for optimization
    param_bounds = Bounds(
        [0.1, 0.14, 0.1],  # Lower bounds
        [0.6, 0.9, 20.0]   # Upper bounds
    )

    print("Initial Parameters:", initial_params) # Print initial parameters

    # Optimization using scipy.optimize.minimize with bounds
    result = minimize(
        target_function,
        initial_params,
        args=(times, climb_rate_ideal, noisy_altitude),
        method="Nelder-Mead",
        bounds=param_bounds # Apply bounds here
    )
    optimized_params = result.x
    print("Optimized Parameters:", optimized_params) # Print optimized parameters
    print("Optimized target value:", result.fun)

    # Run the filter with the optimized parameters and plot results
    tau_1, tau_2, dyn_alpha_divisor = optimized_params

    old_altitude_1 = noisy_altitude[0]
    old_altitude_2 = noisy_altitude[0]
    climb_rate = 0
    delta_t = np.diff(times)
    # insert a value at the beginning to delta_t to keep the length of the arrays consistent
    delta_t = np.insert(delta_t, 0, delta_t[0])

    filtered_climb_rate = np.zeros(len(noisy_altitude))
    for i in range(len(noisy_altitude)):
        dt = delta_t[i]
        old_altitude_1, old_altitude_2, climb_rate = double_exponential_filter(
            noisy_altitude[i],
            old_altitude_1,
            old_altitude_2,
            climb_rate,
            tau_1, tau_2, dyn_alpha_divisor,
            dt
        )
        filtered_climb_rate[i] = climb_rate

    # take the filtered climb rate and calculate the altitude
    filtered_altitude = np.zeros(len(noisy_altitude))
    for i in range(len(noisy_altitude)):
        if i == 0:
            filtered_altitude[i] = noisy_altitude[i]
        else:
            filtered_altitude[i] = filtered_altitude[i-1] + filtered_climb_rate[i] * delta_t[i]

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot altitude on the left y-axis
    ax1.plot(times, noisy_altitude, label="Noisy Altitude (m)", color="blue", linewidth=2)
    ax1.plot(times_ideal_altitude, ideal_altitude, label="Ideal Altitude (m)", color="cyan", linestyle='--')
    ax1.plot(times, filtered_altitude, label="Filtered Altitude (m)", color="red", linewidth=2)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Altitude (m)", color="blue")
    ax1.tick_params(axis='y', labelcolor="blue")

    # Create a second y-axis for climb rate
    ax2 = ax1.twinx()

    min_ideal_cr = np.min(climb_rate_ideal)
    max_ideal_cr = np.max(climb_rate_ideal)
    cr_margin = 0.1 * (max_ideal_cr - min_ideal_cr) # 10% margin
    ax2.set_ylim([min_ideal_cr - cr_margin, max_ideal_cr + cr_margin]) # Set y-axis limits for climb rate

    ax2.plot(times, climb_rate_ideal, label="Ideal Climb Rate (m/s)", color="orange", linestyle='--')

    ax2.plot(times, filtered_climb_rate, label="Smoothed Climb Rate (m/s)", color="green", linewidth=2.5)
    ax2.set_ylabel("Climb Rate (m/s)", color="red")
    ax2.tick_params(axis='y', labelcolor="red")

    plt.title("Artificial Noisy Altitude and Filtered Signals") # Updated title - more concise
    plt.grid(True)
    fig.legend(loc="upper right")
    plt.tight_layout() # Adjust layout to prevent labels from overlapping
    plt.show()