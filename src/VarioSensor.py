
import JetiSensor


class VarioSensor(JetiSensor):
    '''Vario functionality via pressure sensor.

    Args:
        JetiSensor (class): Base class for all sensors
    '''

    def __init__(self) -> None:
        super().__init__()