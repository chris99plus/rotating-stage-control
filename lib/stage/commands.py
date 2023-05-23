from enum import Enum

class Command:
    class Direction(Enum):
        CLOCKWISE = 0
        COUNTERCLOCKWISE = 1

    class Action(Enum):
        EMERGENCY_STOP = 0
        STOP = 1
        RUN_CONTINUOUS = 2
        RUN_TO_ANGLE = 3

    def __init__(self, action: 'Action', direction: 'Direction', speed: float = 1.0, angle: float | None = None) -> None:
        self.action = action
        self.direction = direction
        self.speed = speed
        self.angle = angle