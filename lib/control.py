from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Any, Dict, List, Tuple, cast

from .process import RuntimeEnv, GenericProcess
from .runtime import Runtime
from .sensors import AbsoluteSensor

import time

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, args: List[Any], kwargs: Dict[str, Any]) -> None:
        super().__init__(args, kwargs)
        self.current_angle: float = 0.0
        self.expected_angle: float = 0.0
        self.rotation_speed: float = 0.0
        self.absolute_sensor_values = cast(Connection, kwargs["absolute_sensor_values"])

    def setup(self):
        pass

    def loop(self):
        if self.absolute_sensor_values.poll():
            print("Control reads absolute value:", self.absolute_sensor_values.recv())

    def stop(self):
        pass

class Control(GenericProcess):
    def __init__(self, absolute_sensor: AbsoluteSensor) -> None:
        super().__init__()
        self.absolute_sensor = absolute_sensor
        self.depends(absolute_sensor)

    def init(self) -> Tuple[RuntimeEnv, Connection]:
        signal, runtime_signal = Pipe()
        kwargs = {
            "absolute_sensor_values": self.absolute_sensor.values
        }
        return RuntimeEnv(ControlRuntime, runtime_signal, kwargs=kwargs), signal

    
        