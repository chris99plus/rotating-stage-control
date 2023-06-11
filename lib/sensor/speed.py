from abc import ABC, abstractmethod
import math

from .rotation import RotationSensor
from lib.utility.angle import Angle

class SpeedSensor(ABC):
    def init(self) -> None:
        return
    
    def release(self) -> None:
        return
    
    @abstractmethod
    def measure_speed(self) -> float | None:
        pass

class AngularSpeedSensor(SpeedSensor):
    def __init__(self, angle_sensor: RotationSensor, stage_diameter: float) -> None:
        self.angle_sensor = angle_sensor
        self.stage_diameter = stage_diameter
        self.last_angle_recording: float | None = None
        self.last_angle: Angle | None = None
        self.avg_speed: list[float] = []

    def measure_speed(self) -> float | None:
        # Initialize values if they are not set yet
        if self.last_angle is None:
            if self.angle_sensor.last_angle is not None:
                self.last_angle = self.angle_sensor.last_angle
                self.last_angle_recording = self.angle_sensor.last_angle_recording
            return None
        
        assert self.last_angle is not None and self.last_angle_recording is not None
        sensor_angle = self.angle_sensor.last_angle.round()
        sensor_recording = self.angle_sensor.last_angle_recording
        dt = sensor_recording - self.last_angle_recording
        if dt > 0:
            da = self.last_angle.delta(sensor_angle)
            if da > 0.25:
                s = math.radians(da) * self.stage_diameter / 2
                speed = s / dt
            else:
                speed = 0.0

            # Update values
            self.last_angle_recording = self.angle_sensor.last_angle_recording
            self.last_angle = self.angle_sensor.last_angle.round()
            self.avg_speed.append(speed)
            self.avg_speed = self.avg_speed[-5:]
            return sum(self.avg_speed) / len(self.avg_speed)
        else:
            return None
