from typing import Any
from simple_pid import PID
import math

from .commands import Command
from .motor import FrequencyConverter

def pi_clip(angle):
    if angle > 0:
        if angle > math.pi:
            return angle - 2*math.pi
    else:
        if angle < -math.pi:
            return angle + 2*math.pi
    return angle

class StageAnglePID:
    def __init__(self, max_frequency: float, kp: float, ki: float = 0, kd: float = 0) -> None:
        self._max_frequency = max_frequency
        self._actual_value: float = 0.0
        self._control_frequency: float | None = None
        
        # PID
        self.pid = PID(kp, ki, kd)
        self.pid.sample_time = 0.1 # (100 ms) in secounds
        self.pid.output_limits = (-max_frequency, max_frequency)

    @property
    def max_frequency(self) -> float:
        return self._max_frequency

    @property
    def setpoint(self) -> float:
        return self.pid.setpoint
    
    @setpoint.setter
    def setpoint(self, value) -> None:
        self.pid.set_auto_mode(False)
        self.pid(0)
        self.pid.setpoint = value
        self.pid.set_auto_mode(True, last_output=self._actual_value)

    def update(self, actual_value: float) -> float | None:
        self._control_frequency = self.pid(actual_value)
        return self._control_frequency
    
class StageAngleController:
    def __init__(self, angle_pid: StageAnglePID, actual_angle: float | None = None) -> None:
        self.angle_increment: float = 0.0
        self.actual_angle: float | None = actual_angle
        self.desired_angle: float | None = None
        self.angle_pid = angle_pid
        self.frequency: float | None = None
        self.current_command: Command | None = None

    def set_command(self, cmd: Command) -> bool:
        if self.actual_angle is None:
            return False
        
        self.desired_angle = cmd.angle
        self.angle_increment = 0.0
        if cmd.direction == Command.Direction.CLOCKWISE:
            if self.actual_angle > cmd.angle:
                self.angle_pid.setpoint = 360 - self.actual_angle + cmd.angle
            else:
                self.angle_pid.setpoint = cmd.angle - self.actual_angle 
        elif cmd.direction == Command.Direction.COUNTERCLOCKWISE:
            if self.actual_angle < cmd.angle:
                self.angle_pid.setpoint = self.actual_angle + 360 - cmd.angle
            else:
                self.angle_pid.setpoint = self.actual_angle - cmd.angle
        else:
            raise ValueError("Invalid direction")
        self.current_command = cmd
        return True

    def set_measurement(self, actual_angle: float) -> None:
        assert actual_angle >= 0 and actual_angle < 360
        assert self.angle_increment >= 0 and self.angle_increment < 360

        if self.current_command is not None:
            if self.current_command.direction == Command.Direction.CLOCKWISE:
                if actual_angle > self.actual_angle:
                    self.angle_increment = self.angle_increment + actual_angle - self.actual_angle
                else:
                    self.angle_increment = self.angle_increment + 360 - self.actual_angle + actual_angle
            else:
                if actual_angle < self.actual_angle:
                    self.angle_increment = self.angle_increment + self.actual_angle - actual_angle
                else:
                    self.angle_increment = self.angle_increment + self.actual_angle + 360 - actual_angle
            self.angle_increment %= 360
            frequency = self.angle_pid.update(self.angle_increment)
            self.frequency = 0.0 if abs(frequency) < 1.0 else frequency
        
        self.actual_angle = actual_angle

class StageMotorController:
    def __init__(self, angle_controller: StageAngleController, converter: FrequencyConverter) -> None:
        self.angle_controller = angle_controller
        self.converter = converter
        self.actual_frequency: float = 0.0
        self.motor_running: bool = False
        self.motor_running_forward: bool = True 

    @property
    def is_running_forward(self) -> bool:
        direction = self.angle_controller.current_command.direction == Command.Direction.CLOCKWISE
        return direction if self.desired_frequency > 0 else not direction
    
    @property
    def desired_frequency(self) -> float | None:
        freq = self.angle_controller.frequency or 0.0
        return round(freq, 2)

    def emergency_stop(self) -> None:
        self.converter.emergency_stop()
        self.motor_running = False


    def update(self) -> bool:
        # Check if update can be made
        if self.angle_controller.frequency is None:
            return False
        
        desired_frequency = round(self.angle_controller.frequency, 2)
        if abs(desired_frequency) < 1.0 and self.motor_running:
            self.converter.stop()
            self.motor_running = False
            return True
        elif abs(desired_frequency) >= 1.0 and not self.motor_running:
            self.motor_running_forward = self.is_running_forward
            self.motor_running = True
            self.converter.run(self.motor_running_forward)
            return True

        if self.actual_frequency != desired_frequency:
            self.converter.set_target_frequency(abs(desired_frequency))
            self.actual_frequency = desired_frequency
            return True
        return False
