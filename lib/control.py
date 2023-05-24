from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple
import math

from .process import RuntimeEnvironment, GenericProcess
from .runtime import Runtime, App
from .sensors import AbsoluteSensor
from .view import View
from .stage.controller import StageController
from .stage.commands import Command
from .stage.motor import FrequencyConverter, JSLSM100Converter

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, commands: Connection, absolute_sensor_values: Connection, app: App) -> None:
        super().__init__()
        self.app = app
        self.controller = StageController()
        self.motor: FrequencyConverter = None
        self.commands = commands
        self.absolute_sensor_values = absolute_sensor_values
        self.current_angle: float = None

    def setup(self):
        # self.motor = JSLSM100Converter(1)
        self.controller(Command(Command.Action.RUN_TO_ANGLE, Command.Direction.CLOCKWISE, 1, 180.0))

    def loop(self):
        if self.commands.poll():
            self.controller(self.commands.recv())
        
        if self.absolute_sensor_values.poll():
            self.current_angle = self.absolute_sensor_values.recv()
            self.controller.update(self.current_angle)
            # print("Expected: %.2f, control %.2f" % (self.current_angle, self.controller.frequency))
            self.app.send((math.radians(self.current_angle), self.controller.frequency))

    def stop(self):
        pass

class Control(GenericProcess):
    def __init__(self, view: View, absolute_sensor: AbsoluteSensor) -> None:
        super().__init__()
        self.view = view
        self.absolute_sensor = absolute_sensor
        self.depends(view)
        self.depends(absolute_sensor)

    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        kwargs = {
            "absolute_sensor_values": self.absolute_sensor.values,
            "commands": self.view.commands
        }
        return RuntimeEnvironment(ControlRuntime, runtime_signal, kwargs=kwargs), signal

    
        