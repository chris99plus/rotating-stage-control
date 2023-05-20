from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple

from .process import RuntimeEnvironment, GenericProcess
from .runtime import Runtime
from .sensors import AbsoluteSensor

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, absolute_sensor_values: Connection) -> None:
        super().__init__()
        self.current_angle: float = 0.0
        self.expected_angle: float = 0.0
        self.rotation_speed: float = 0.0
        self.absolute_sensor_values = absolute_sensor_values

    def setup(self):
        pass

    def loop(self):
        if self.absolute_sensor_values.poll():
            self.current_angle = self.absolute_sensor_values.recv()
            print("Control reads absolute value:", self.current_angle)

    def stop(self):
        pass

class Control(GenericProcess):
    def __init__(self, absolute_sensor: AbsoluteSensor) -> None:
        super().__init__()
        self.absolute_sensor = absolute_sensor
        self.depends(absolute_sensor)

    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        kwargs = {
            "absolute_sensor_values": self.absolute_sensor.values
        }
        return RuntimeEnvironment(ControlRuntime, runtime_signal, kwargs=kwargs), signal

    
        