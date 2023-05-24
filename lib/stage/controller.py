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
    def __init__(self, max_frequency: float = 60.0) -> None:
        self.pid: PID | None = None
        self.cmd: Command = Command(Command.Action.STOP)
        self.max_frequency: float = max_frequency
        self.frequency = 0.0
        self.angle = -1.0

    def __call__(self, cmd: Command) -> None:
        last_cmd = self.cmd
        self.cmd = cmd

        if self.pid is None:
            self.pid = PID(10, 5, 1)
            self.pid.error_map = pi_clip
            self.pid.sample_time = 0.1 # (100 ms) in seconds

        if cmd.is_run():
            if last_cmd.is_stop():
                self.pid.set_auto_mode(True, last_output=self.frequency)
            self.pid.setpoint = math.radians(self.cmd.angle) - math.pi
            self.pid.output_limits = (-self.max_frequency * self.cmd.speed, self.max_frequency * self.cmd.speed)
        else:
            self.pid.set_auto_mode(False)
            self.frequency = 0.0

    def update(self, angle: float) -> bool:
        """Angle of the sage in degrees"""
        assert angle >= 0 and angle < 360, "Expect angle to have a value range of [0, 360)"
        self.angle = angle

        last_frequency = self.frequency
        if self.pid is not None and self.cmd.is_run():
            self.frequency = self.pid(math.radians(angle) - math.pi) or 0.0
        else:
            self.frequency = 0.0

        if last_frequency != self.frequency:
            return True
            