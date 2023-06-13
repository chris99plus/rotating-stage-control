from abc import ABC, abstractmethod
import math

from .rotation import RotationSensor
from lib.utility.angle import Angle, angle_avg

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
        self.last_angle: Angle | None = None
        self.last_angle_recording: float | None = None
        self.last_angle_recording_avg: list[float] = []
        self.last_angle_avg: list[Angle] = []

    def measure_speed(self) -> float | None:
        # Initialize values if they are not set yet
        if self.last_angle is None:
            if self.angle_sensor.last_angle is not None:
                self.last_angle_avg.append(self.angle_sensor.last_angle)
                self.last_angle = self.angle_sensor.last_angle
                self.last_angle_recording_avg.append(self.angle_sensor.last_angle_recording)
                self.last_angle_recording = self.angle_sensor.last_angle_recording
            return None
        
        assert self.last_angle is not None and self.last_angle_recording is not None   
        self.last_angle_recording_avg.append(self.angle_sensor.last_angle_recording)
        self.last_angle_avg.append(self.angle_sensor.last_angle)
        sensor_recording = sum(self.last_angle_recording_avg) / len(self.last_angle_recording_avg)
        sensor_angle = angle_avg(self.last_angle_avg)
        dt = sensor_recording - self.last_angle_recording
        if dt > 0:
            da = self.last_angle.delta(sensor_angle)
            s = math.radians(da) * self.stage_diameter / 2
            speed = s / dt

            # Update values
            self.last_angle_recording_avg = self.last_angle_recording_avg[-10:]
            self.last_angle_avg = self.last_angle_avg[-10:]
            self.last_angle = sensor_angle
            self.last_angle_recording = sensor_recording
            return speed
        else:
            return None
