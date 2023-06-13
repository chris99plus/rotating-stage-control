from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple, cast
from time import time

from .process import RuntimeEnvironment, GenericProcess
from .runtime import Runtime, App
from .sensors import Sensor, AbsoluteSensor
from .view import View
from .stage.commands import Command
from .stage.motor import JSLSM100Converter, TestConverter
from .utility.angle import Angle
from .stage.control import StageControl
from .stage.controller import StageAngleController, StageSpeedController 

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
        self.control: StageControl = None

        # State
        self.last_debug: float = time()
        self.last_measurement: float = time()

    def setup(self):
        converter = JSLSM100Converter(
                self.app.get_config('motor', 'address', int, 1),
                self.app.get_config('motor', 'port', str, '/dev/serial0')) \
            if not self.app.is_testing_enabled else TestConverter()
        
        # Controller
        angle_controller = StageAngleController(
            self.app.get_config('control', 'angle_pid_kp', float, 2),
            self.app.get_config('control', 'angle_pid_ki', float, 0),
            self.app.get_config('control', 'angle_pid_kd', float, 0))
        speed_controller = StageSpeedController(
            self.app.get_config('motor', 'max_frequency', float, 40.0),
            self.app.get_config('control', 'speed_pid_kp', float, 10),
            self.app.get_config('control', 'speed_pid_ki', float, 10),
            self.app.get_config('control', 'speed_pid_kd', float, 0))
        self.control = StageControl(converter, angle_controller, speed_controller)

        # Config
        self.max_measurement_duration = self.app.get_config('control', 'max_measurement_duration', int, 100) / 1000
        self.max_speed = self.app.get_config('DEFAULT', 'max_speed', float, 1.0)

    def loop(self):
        # Update sensor values
        sensor_values: list[tuple[Sensor, float]] | None = None
        if self.sensor_values.poll():
            sensor_values = cast(list[tuple[Sensor, float]], self.sensor_values.recv())
            self.last_measurement = time()

        # Check angle update duration. If this class is missing angle updates
        # the stage rotation should be stopped immediately.
        if time() - self.last_measurement > self.max_measurement_duration:
            sensor_values = []
            self.control.set_activity(Command(Command.Action.EMERGENCY_STOP))

        # Update controller and send control values if testing is enabled. 
        if self.control(sensor_values) and self.app.is_testing_enabled:
            self.sensor_values.send(('debug', self.control.motor_running_forward, self.control.motor.get_target_frequency()))

        # Update commands
        if self.commands.poll():
            command = self.commands.recv()
            assert isinstance(command, Command), "Received non command type from the command connection"
            if command.speed > self.max_speed:
                command.speed = self.max_speed
            if not self.control.set_activity(command):
                print("[WARN] Failed to set activity")

        # Update debug
        if self.app.is_debug_enabled and time() - self.last_debug > 0.2:
            if self.control.angle_controller._actual_angle is not None and \
                self.control.speed_controller.frequency is not None:
                self.app.send((self.control.angle_controller._actual_angle, self.control.speed_controller.frequency))
                self.last_debug = time()

    def stop(self) -> int | None:
        self.control.motor.set_target_frequency(0)
        self.control.motor.stop()

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

    
        