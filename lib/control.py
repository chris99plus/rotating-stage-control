from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple, cast
from time import time

from .process import RuntimeEnvironment, GenericProcess
from .runtime import Runtime, App
from .sensors import Sensor, AbsoluteSensor
from .view import View
from .stage.controller import StageMotorController, StageAngleController, StageAnglePID
from .stage.commands import Command
from .stage.motor import JSLSM100Converter, TestConverter
from .utility.angle import Angle

# The control process collects any data getting to the system. It contains
# sensor readings and input commands.
class ControlRuntime(Runtime):
    def __init__(self, cmds: Connection, asv: Connection, app: App) -> None:
        super().__init__()
        self.app = app

        # Connections
        self.commands = cmds
        self.sensor_values = asv

        # Function classes
        self.controller: StageMotorController = None

        # State
        self.last_debug: float = time()
        self.last_measurement: float = time()
        self.active_command: Command = Command(Command.Action.STOP)

    def setup(self):
        converter = JSLSM100Converter(self.app.get_config('motor', 'address', int, 1)) if not self.app.is_testing_enabled else TestConverter()
        angle_pid = StageAnglePID(
            self.app.get_config('motor', 'max_frequency', float, 40),
            self.app.get_config('motor', 'min_frequency', float, 0.5),
            self.app.get_config('control', 'angle_pid_kp', float, 2))
        angle_controller = StageAngleController(angle_pid)
        self.controller = StageMotorController(angle_controller, converter)

        # Config
        self.max_measurement_duration = self.app.get_config('control', 'max_measurement_duration', int, 100) / 1000
        self.stop_angle = self.app.get_config('control', 'stop_angle', float, 90.0)

    def loop(self):
        # Update controller
        if self.controller.update() and self.app.is_testing_enabled:
            self.sensor_values.send((self.controller.motor_running_forward, self.controller.converter.get_current_frequency()))

        # Update sensor values 
        if self.sensor_values.poll():
            values = cast(list[tuple[Sensor, float]], self.sensor_values.recv())
            for sensor, value in values:
                assert isinstance(value, float)
                if sensor == Sensor.STAGE_ABSOLUTE_ANGLE:
                    self.controller.angle_controller.set_measurement(value)
                elif sensor == Sensor.STAGE_SPEED:
                    pass
                    # TODO: Use speed values
            self.last_measurement = time()

        # Check angle update duration. If this class is missing angle updates
        # the stage rotation should be stopped immediately.
        if time() - self.last_measurement > self.max_measurement_duration:
            invalid_readings = True
            self.emergency_stop()
        else:
            invalid_readings = False

        # Update commands
        if self.commands.poll():
            cmd = self.commands.recv()
            assert isinstance(cmd, Command), "Received non command type from the command connection"
            
            if cmd.action == Command.Action.EMERGENCY_STOP:
                self.emergency_stop()

            # Update commands only if angle measurements are present. Otherwise
            # the rotation is stopped.
            if not invalid_readings:
                last_active_command = self.active_command
                self.active_command = cmd
                if cmd.action == Command.Action.RUN_TO_ANGLE:
                    if not self.controller.angle_controller.set_command(cmd):
                        raise Exception("Could not set RUN_TO_ANGLE command on angle controller")
                elif cmd.action == Command.Action.RUN_CONTINUOUS:
                    self.set_intermediate_RUN_TO_ANGLE_command(270)
                elif cmd.action == Command.Action.STOP:
                    if not self.controller.stopped:
                        self.active_command = Command(cmd.action, last_active_command.direction, cmd.speed)
                        self.set_intermediate_RUN_TO_ANGLE_command(self.stop_angle * cmd.speed)
                else:
                    raise ValueError("Unknown command action")

        # Update intermediate command of RUN_CONTINUOUS
        if self.active_command.action == Command.Action.RUN_CONTINUOUS:
            if self.controller.angle_controller.progress > 50:
                self.set_intermediate_RUN_TO_ANGLE_command(270)

        # Update debug
        if self.app.is_debug_enabled and time() - self.last_debug > 0.2 and self.controller.angle_controller.actual_angle is not None:
            self.app.send((self.controller.angle_controller.actual_angle, abs(self.controller.actual_frequency)))
            self.last_debug = time()

    def stop(self):
        self.controller.converter.stop()

    def emergency_stop(self):
        self.controller.emergency_stop()
        self.active_command = Command(Command.Action.EMERGENCY_STOP)

    def set_intermediate_RUN_TO_ANGLE_command(self, angle: float):
        cur_angle = Angle(self.controller.angle_controller.actual_angle)
        int_angle = cur_angle + angle if self.active_command.direction == Command.Direction.CLOCKWISE else cur_angle - angle
        int_cmd = Command(Command.Action.RUN_TO_ANGLE, self.active_command.direction, self.active_command.speed, float(int_angle))
        if not self.controller.angle_controller.set_command(int_cmd):
            raise Exception("Could not set intermediate command on angle controller")

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

    
        