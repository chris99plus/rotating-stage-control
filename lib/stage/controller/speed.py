from typing import Any
from simple_pid import PID

# Controls the frequency of the motor based on the expected and actual speed of
# the stage.
class StageSpeedController:
    def __init__(self, max_frequency: float, kp: float) -> None:
        self._control_frequency: float | None = None
        self._desired_speed: float | None = None
        self._actual_speed: float | None = None

        # PID
        self._pid = PID(kp)
        self._pid.sample_time = 0.05 # (50 ms)
        self._pid.output_limits = (0, max_frequency)

    @property
    def frequency(self) -> float | None:
        return self._control_frequency
    
    @property
    def actual_speed(self) -> float | None:
        return self._actual_speed

    def __call__(self, actual: float) -> float:
        if self._desired_speed is not None:
            self._control_frequency = self._pid(actual)

        self._actual_speed = actual
        return self._control_frequency
    
    @property
    def setpoint(self) -> float:
        return self._desired_speed
    
    def set_setpoint(self, speed: float) -> bool:
        if self._actual_speed is None:
            return False
        
        # Configure PID
        self._pid.setpoint = speed

        self._desired_speed = speed
        return True