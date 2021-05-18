
import JetiSensor


class VoltageSensor(JetiSensor):
    '''Measure voltage levels

    Args:
        JetiSensor (class): Base class for all sensors
    '''

    def __init__(self) -> None:
        super().__init__()