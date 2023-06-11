from simple_pid import PID

from lib.utility.angle import Angle

# This class controls the speed based on a desired angle which is requested by
# the user.
class StageAngleController:
    def __init__(self, kp: float) -> None:
        self._control_speed: float | None = None
        self._angle_increment = Angle(0)
        self._desired_angle: Angle | None = None
        self._turning_clockwise: bool = True
        self._actual_angle: Angle | None = None
        
        # PID
        self._pid = PID(kp)
        self._pid.sample_time = 0.1 # (100 ms)
        self._pid.output_limits = (-1.0 , 1.0) # -1 m/s to 1 m/s

    @property
    def speed(self) -> float:
        return self._control_speed

    # Update controller with new angle of the stage
    def __call__(self, actual: Angle) -> float:
        if self._desired_angle is not None:
            if self._turning_clockwise:
                if actual > self._actual_angle:
                    self._angle_increment = self._angle_increment + actual - self._actual_angle
                else:
                    self._angle_increment = self._angle_increment + 360 - self._actual_angle + actual
            else:
                if actual < self._actual_angle:
                    self._angle_increment = self._angle_increment + self._actual_angle - actual
                else:
                    self._angle_increment = self._angle_increment + self._actual_angle + 360 - actual
            self._control_speed = self._pid(float(actual))

        self._actual_angle = actual
        return self._control_speed

    @property
    def setpoint(self) -> Angle:
        return self._desired_angle

    # Set a new desired angle of the stage with the speed it should run with.
    def set_setpoint(self, angle: Angle, speed: float, clockwise: bool) -> bool:
        if self._actual_angle is None:
            return False
        
        # Calculate control angle
        if clockwise:
            if self._actual_angle > angle:
                control_angle = Angle(360) - self._actual_angle + angle
            else:
                control_angle = angle - self._actual_angle
        else:
            if self._actual_angle < angle:
                control_angle = self._actual_angle + 360 - angle
            else:
                control_angle = self._actual_angle - angle

        # Configure PID with control speed
        self._pid.set_auto_mode(False)
        self._pid(0)
        self._pid.setpoint = control_angle
        self._pid.output_limits = (-1 * speed, speed)
        self._pid.set_auto_mode(True, last_output=self._control_speed)
        
        self._desired_angle = angle
        self._turning_clockwise = clockwise
        return True
