from micropython import const

CAL_DATA_C1 = const(0xA2)
CAL_DATA_C2 = const(0xA4)
CAL_DATA_C3 = const(0xA6)
CAL_DATA_C4 = const(0xA8)
CAL_DATA_C5 = const(0xAA)
CAL_DATA_C6 = const(0xAC)
DATA = const(0x00)

TEMP_OSR_256 = const(0)
TEMP_OSR_512 = const(1)
TEMP_OSR_1024 = const(2)
TEMP_OSR_2048 = const(3)
TEMP_OSR_4096 = const(4)
temperature_oversample_rate_values = (
    TEMP_OSR_256,
    TEMP_OSR_512,
    TEMP_OSR_1024,
    TEMP_OSR_2048,
    TEMP_OSR_4096,
)
temp_command_values = {
    TEMP_OSR_256: 0x50,
    TEMP_OSR_512: 0x52,
    TEMP_OSR_1024: 0x54,
    TEMP_OSR_2048: 0x56,
    TEMP_OSR_4096: 0x58,
}

PRESS_OSR_256 = const(0)
PRESS_OSR_512 = const(1)
PRESS_OSR_1024 = const(2)
PRESS_OSR_2048 = const(3)
PRESS_OSR_4096 = const(4)
pressure_oversample_rate_values = (
    PRESS_OSR_256,
    PRESS_OSR_512,
    PRESS_OSR_1024,
    PRESS_OSR_2048,
    PRESS_OSR_4096,
)
pressure_command_values = {
    PRESS_OSR_256: 0x40,
    PRESS_OSR_512: 0x42,
    PRESS_OSR_1024: 0x44,
    PRESS_OSR_2048: 0x46,
    PRESS_OSR_4096: 0x48,
}

# Conversion times for each oversampling rate (in milliseconds)
conversion_times = {
    TEMP_OSR_256: 1,
    TEMP_OSR_512: 2,
    TEMP_OSR_1024: 3,
    TEMP_OSR_2048: 5,
    TEMP_OSR_4096: 10,
    PRESS_OSR_256: 1,
    PRESS_OSR_512: 2,
    PRESS_OSR_1024: 3,
    PRESS_OSR_2048: 5,
    PRESS_OSR_4096: 10,
}
