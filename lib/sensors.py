from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple
from time import time

from .runtime import Runtime
from .process import GenericProcess, RuntimeEnvironment
from .sensor.rotation import RotationSensor, OpticalRotationSensor

class AbsoluteSensorRuntime(Runtime):
    def __init__(self, values: Connection) -> None:
        super().__init__()
        self.values = values
        self.current_angle: float | None = None
        self.last_value_time: float = time()

        # Function classes
        self.sensor: RotationSensor = None

    def setup(self) -> None:
        self.sensor = OpticalRotationSensor()
        self.sensor.init()

    def loop(self) -> None:
        measurement = self.sensor.measure_angle()
        if measurement is not None:
            assert measurement >= 0.0 and measurement < 360, "Expect angle measurement in range of [0, 360)"
            self.current_angle = measurement
            self.last_value_time = time()
            self.values.send(self.current_angle)

        # Check if values come regularly
        if time() - self.last_value_time > 1:
            raise Exception("Not enough angles measured in time")

    def stop(self) -> int | None:
        self.sensor.release()

class AbsoluteSensor(GenericProcess):
    def __init__(self) -> None:
        super().__init__()

    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        self.values, runtime_value = Pipe()
        kwargs = {
            "values": runtime_value
        }
        return RuntimeEnvironment(AbsoluteSensorRuntime, runtime_signal, kwargs=kwargs), signal
