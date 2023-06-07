from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple
from time import time

from .process import RuntimeEnvironment, GenericProcess
from .runtime import Runtime, App
from .sensors import AbsoluteSensor
from .view import View
from .stage.controller import StageMotorController, StageAngleController, StageAnglePID
from .stage.commands import Command
from .stage.motor import JSLSM100Converter, TestConverter

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, cmds: Connection, asv: Connection, app: App) -> None:
        super().__init__()
        self.app = app

        # Connections
        self.commands = cmds
        self.absolute_sensor_values = asv

        # Function classes
        self.motor_controller: StageMotorController = None

        # State
        self.last_debug: float = time()

    def setup(self):
        converter = JSLSM100Converter(1) if not self.app.is_testing_enabled else TestConverter()
        angle_pid = StageAnglePID(30, 2)
        angle_controller = StageAngleController(angle_pid)
        self.controller = StageMotorController(angle_controller, converter)

    def loop(self):
        # Update controller
        if self.controller.update() and self.app.is_testing_enabled:
            self.absolute_sensor_values.send((self.controller.motor_running_forward, self.controller.converter.get_current_frequency()))

        # Update angles
        if self.absolute_sensor_values.poll():
            actual_angle = self.absolute_sensor_values.recv()
            self.controller.angle_controller.set_measurement(actual_angle)

        # Update commands
        if self.commands.poll():
            cmd = self.commands.recv()
            assert isinstance(cmd, Command), "Received non command type from the command connection"
            
            if cmd.action == Command.Action.EMERGENCY_STOP:
                self.controller.emergency_stop()
            elif cmd.action == Command.Action.RUN_TO_ANGLE:
                if not self.controller.angle_controller.set_command(cmd):
                    # TODO: Notify, that set command does not work at the moment
                    pass
            else:
                # TODO: Other modes
                pass

        # Update debug
        if self.app.is_debug_enabled and time() - self.last_debug > 0.2 and self.controller.angle_controller.actual_angle is not None:
            self.app.send((self.controller.angle_controller.actual_angle, abs(self.controller.actual_frequency)))
            self.last_debug = time()

    def stop(self):
        self.controller.converter.stop()

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
            "asv": self.absolute_sensor.values,
            "cmds": self.view.commands
        }
        return RuntimeEnvironment(ControlRuntime, runtime_signal, kwargs=kwargs), signal

    
        