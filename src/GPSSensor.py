
import JetiSensor


class GPSSensor(JetiSensor):
    '''GPS data handling

    Args:
        JetiSensor (class): Base class for all sensors
    '''

    def __init__(self) -> None:
        super().__init__()