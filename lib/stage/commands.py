from enum import Enum

class Command:
    class Direction(Enum):
        NONE = 0
        CLOCKWISE = 1
        COUNTERCLOCKWISE = 2

    class Action(Enum):
        EMERGENCY_STOP = 0
        STOP = 1
        RUN_CONTINUOUS = 2
        RUN_TO_ANGLE = 3

    def __init__(self, action: 'Action', direction: 'Direction' = Direction.NONE, speed: float = 1.0, angle: float | None = None) -> None:
        if action == Command.Action.RUN_TO_ANGLE:
            assert angle >= 0 and angle < 360, 'Expect angle in degree between 0 and 360 [0, 360)'
        if direction == Command.Direction.NONE:
            assert action == Command.Action.EMERGENCY_STOP or action == Command.Action.STOP, 'Expect direction for run commands'
        self.action = action
        self.direction = direction
        self.speed = speed
        self.angle = angle

    @property
    def turn_clockwise(self) -> bool:
        return self.direction == Command.Direction.CLOCKWISE

    def is_run(self) -> bool:
        return self.action == Command.Action.RUN_CONTINUOUS or \
               self.action == Command.Action.RUN_TO_ANGLE
    
    def is_stop(self) -> bool:
        return self.action == Command.Action.EMERGENCY_STOP or \
               self.action == Command.Action.STOP
