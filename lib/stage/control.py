from .motor import FrequencyConverter
from .controller.angle import StageAngleController
from .controller.speed import StageSpeedController
from .commands import Command
from lib.sensor import Sensor
from lib.utility.angle import Angle
from time import time

class StageControl:
    def __init__(self, motor: FrequencyConverter, angle_controller: StageAngleController, speed_controller: StageSpeedController, max_frequency: float) -> None:
        # Controller
        self.motor = motor
        self.angle_controller = angle_controller
        self.speed_controller = speed_controller

        # State
        self.motor_running: bool = False
        self.motor_running_forward: bool = True
        self._active_command: Command | None = None

        self.max_frequency = max_frequency
        self.last_update = time()

    @property
    def stopped(self) -> bool:
        return not self.motor_running
    
    # Update motor controls
    def __call__(self, readings: list[tuple[Sensor, float]] | None) -> bool:
        # Update sensor readings on the controllers
        if readings is not None:
            for sensor, value in readings:
                assert isinstance(value, float)
                if sensor == Sensor.STAGE_ABSOLUTE_ANGLE:
                    self.angle_controller(Angle(value))
                elif sensor == Sensor.STAGE_SPEED:
                    self.speed_controller(value)
                else:
                    raise ValueError("Unknown sensor")

        if self._active_command is not None and \
            self._active_command.action != Command.Action.REMOTE:
            # Update speed controller with speeds from the angle controller, if the
            # angle used for control.
            if self._active_command is not None and \
                self._active_command.action == Command.Action.RUN_TO_ANGLE:
                self.speed_controller.set_setpoint(self.angle_controller.speed)

            # Updates are possible only if a frequency was calculated by the speed
            # controller.
            if self.speed_controller.frequency is None or \
                (self.speed_controller.frequency is None and \
                self.angle_controller.speed is None):
                return False
        
            # Control motor and update parameters
            frequency = round(self.speed_controller.frequency, 2)
            if self.angle_controller.speed is None:
                assert self.speed_controller.actual_speed is not None
                speed = self.speed_controller.actual_speed
            else:
                speed = self.angle_controller.speed
        elif self._active_command is not None and \
            self._active_command.action == Command.Action.REMOTE:
            assert self._active_command.frequency is not None
            frequency = self._active_command.frequency * self.max_frequency
            speed = 0
        else:
            frequency = 0
            speed = 0
        assert frequency >= 0

        # if self.motor.is_emergency_stop_active():
        #     self._active_command = Command(Command.Action.EMERGENCY_STOP)
        #     self.motor.stop()
        #     self.motor.set_target_frequency(0)
        #     return True
        if frequency < 1.0 and self.motor_running:
            self.motor.stop()
            self.motor.set_target_frequency(0)
            self.motor_running = False
            return True
        elif frequency >= 1.0 and not self.motor_running:
            turn_forward = self._active_command.turn_clockwise
            turn_forward = turn_forward if speed >= 0 else not turn_forward
            self.motor_running_forward = turn_forward
            self.motor_running = True
            self.motor.run(turn_forward)
            self.motor.set_target_frequency(frequency)
            return True
        
        if time() - self.last_update > 0.1:
            self.last_update = time()
            target_frequency = round(self.motor.get_target_frequency(), 2)
            if frequency != target_frequency and self.motor_running:
                if frequency >= 0.5:
                    self.motor.set_target_frequency(frequency)
                return True

        return False

    @property
    def activity(self) -> Command | None:
        return self._active_command
    
    def set_activity(self, command: Command) -> bool:
        if command.action == Command.Action.EMERGENCY_STOP:
            self.motor.emergency_stop()
            success = True
        elif command.action == Command.Action.STOP:
            success = self.speed_controller.set_setpoint(0)
        elif command.action == Command.Action.RUN_TO_ANGLE:
            success = self.angle_controller.set_setpoint(Angle(command.angle), command.speed, command.turn_clockwise)
        elif command.action == Command.Action.RUN_CONTINUOUS:
            success = self.speed_controller.set_setpoint(command.speed)
        elif command.action == Command.Action.REMOTE:
            self.speed_controller.set_setpoint(0)
            success = True
        else:
            raise ValueError("Unknown command action")

        if success:
            self._active_command = command
            return True
        else:
            return False