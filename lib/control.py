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
from .stage.motor import FrequencyConverter, JSLSM100Converter, TestConverter

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, cmds: Connection, asv: Connection, app: App, testing: bool) -> None:
        super().__init__()
        self.app = app

        # Connections
        self.commands = cmds
        self.absolute_sensor_values = asv

        # Function classes
        self.controller: StageController = None
        self.motor: FrequencyConverter = None

        # State
        self.testing: bool = testing
        self.current_angle: float = None
        self.motor_running: bool = False
        self.motor_running_forward: bool = True

    def motor_run(self, forward: bool):
        if not self.motor_running or self.motor_running_forward != forward:
            self.motor.run(forward)
            self.motor_running_forward = forward
            self.motor_running = True

    def motor_stop(self):
        if self.motor_running:
            self.motor.stop()
            self.motor_running = False

    def motor_turn_forward(self, frequency: float, direction: Command.Direction) -> bool:
        turn_forward = direction == Command.Direction.CLOCKWISE
        if frequency > 0.0:
            return turn_forward
        elif self.controller.frequency < 0.0:
            return not turn_forward

    def setup(self):
        self.controller = StageController()
        self.motor = JSLSM100Converter(1) if not self.testing else TestConverter()

    def loop(self):
        if self.commands.poll():
            cmd = self.commands.recv()
            assert isinstance(cmd, Command), "Received non command type from the command connection"
            self.controller(cmd)

            if cmd.action == Command.Action.EMERGENCY_STOP:
                self.motor.emergency_stop()
                self.motor_running = False
        
        if self.absolute_sensor_values.poll():
            self.current_angle = self.absolute_sensor_values.recv()

            if self.controller.update(self.current_angle):
                self.motor.set_target_frequency(abs(self.controller.frequency))
                self.app.send((self.current_angle, abs(self.controller.frequency)))

                if math.isclose(self.controller.frequency, 0, rel_tol=1e-5):
                    self.motor_stop()
                else:
                    self.motor_run(self.motor_turn_forward(self.controller.frequency, self.controller.cmd.direction))

    def stop(self):
        self.motor.stop()

class Control(GenericProcess):
    def __init__(self, view: View, absolute_sensor: AbsoluteSensor, testing: bool = False) -> None:
        super().__init__()
        self.view = view
        self.absolute_sensor = absolute_sensor
        self.testing = testing
        self.depends(view)
        self.depends(absolute_sensor)

    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        kwargs = {
            "asv": self.absolute_sensor.values,
            "cmds": self.view.commands,
            "testing": self.testing
        }
        return RuntimeEnvironment(ControlRuntime, runtime_signal, kwargs=kwargs), signal

    
        