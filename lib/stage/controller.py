from simple_pid import PID
import math

from .commands import Command

def pi_clip(angle):
    if angle > 0:
        if angle > math.pi:
            return angle - 2*math.pi
    else:
        if angle < -math.pi:
            return angle + 2*math.pi
    return angle

class StageController:
    """PID controller controlling the frequency of the converter to get the
    desired angle."""
    def __init__(self, frequency_limits: tuple[float, float] = (0, 60.0)) -> None:
        self.pid: PID | None = None
        self.cmd: Command = Command(Command.Action.STOP)
        self.frequency_limits: tuple[float, float] = frequency_limits
        self.frequency = 0.0

    def __call__(self, cmd: Command) -> None:
        last_cmd = self.cmd
        self.cmd = cmd

        if self.pid is None:
            self.pid = PID(20, 10, 5)
            self.pid.error_map = pi_clip

        if cmd.is_run():
            if last_cmd.is_stop():
                self.pid.set_auto_mode(True, last_output=self.frequency)
            self.pid.setpoint = math.radians(self.cmd.angle) - math.pi
            self.pid.output_limits = (self.frequency_limits[0], self.frequency_limits[1] * self.cmd.speed)
        else:
            self.pid.set_auto_mode(False)
            self.frequency = 0.0

    def update(self, angle: float) -> None:
        """Angle of the sage in degrees"""
        if self.pid is not None and self.cmd.is_run():
            self.frequency = self.pid(math.radians(angle) - math.pi)
        else:
            self.frequency = 0.0