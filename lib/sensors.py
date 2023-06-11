from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple, cast
from time import time

from .runtime import Runtime, App
from .process import GenericProcess, RuntimeEnvironment
from .sensor.rotation import RotationSensor, OpticalRotationSensor, TestRotationSensor
from .sensor.speed import SpeedSensor, AngularSpeedSensor
from .sensor import Sensor

class AbsoluteSensorRuntime(Runtime):
    def __init__(self, values: Connection, app: App) -> None:
        super().__init__()
        self.app = app

        # Connections
        self.values = values

        # Function classes
        self.angle_sensor: RotationSensor = None
        self.speed_sensor: SpeedSensor = None

        # State
        self.current_angle: float | None = None
        self.current_speed: float | None = None
        self.last_angle_measurement: float = None
        self.last_speed_measurement: float = None

        # Const
        self.angle_sensor_timeout = self.app.get_config('sensors', 'angle_sensor_timeout', float, 1)
        self.speed_sensor_timeout = self.app.get_config('sensors', 'speed_sensor_timeout', float, 1)

    def setup(self) -> None:
        self.angle_sensor = OpticalRotationSensor(self.app.get_config('sensors', 'camera_index', int, 0)) if not self.app.is_testing_enabled else TestRotationSensor()
        self.speed_sensor = AngularSpeedSensor(self.angle_sensor, self.app.get_config('DEFAULT', 'stage_diameter', float, 4.5))
        self.angle_sensor.init()
        self.speed_sensor.init()

        self.last_angle_measurement = time()
        self.last_speed_measurement = time()

    def loop(self) -> None:
        send_queue: list[tuple[Sensor, float]] = []

        angle = self.angle_sensor.measure_angle()
        if angle is not None:
            self.current_angle = angle
            self.last_angle_measurement = time()
            send_queue.append((Sensor.STAGE_ABSOLUTE_ANGLE, float(self.current_angle)))

        speed = self.speed_sensor.measure_speed()
        if speed is not None:
            self.current_speed = speed
            self.last_speed_measurement = time()
            send_queue.append((Sensor.STAGE_SPEED, self.current_speed))

        # Check if values come regularly
        if time() - self.last_angle_measurement > self.angle_sensor_timeout:
            raise Exception("Not enough absolute angles measured in time")
        
        if time() - self.last_speed_measurement > self.speed_sensor_timeout:
            raise Exception("Not enough speed points measured in time")

        if self.app.is_testing_enabled and self.values.poll():
            cast(TestRotationSensor, self.angle_sensor).update(*self.values.recv())

        if len(send_queue) > 0:
            self.values.send(send_queue)

    def stop(self) -> int | None:
        self.speed_sensor.release()
        self.angle_sensor.release()

class AbsoluteSensor(GenericProcess):
    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        self.values, runtime_value = Pipe()
        kwargs = {
            "values": runtime_value
        }
        return RuntimeEnvironment(AbsoluteSensorRuntime, runtime_signal, kwargs=kwargs), signal
