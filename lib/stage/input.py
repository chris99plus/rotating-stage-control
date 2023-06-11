from typing import Any
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

from .commands import Command

# The stage state class keeps track of input request and maps them to desired
# commands, which are send to the control process.
class StageInputState:
    def __init__(self) -> None:
        self.action = Command.Action.STOP
        self.direction = Command.Direction.CLOCKWISE
        self.speed = 0.0
        self.angle = 0.0

    @property
    def command(self) -> Command:
        if self.action == Command.Action.EMERGENCY_STOP or \
            self.action == Command.Action.STOP:
            return Command(self.action, self.direction)
        elif self.action == Command.Action.RUN_CONTINUOUS:
            return Command(self.action, self.direction, self.speed)
        elif self.action == Command.Action.RUN_TO_ANGLE:
            return Command(self.action, self.direction, self.speed, self.angle)
        else:
            raise ValueError("Unknown command action")
    
    def changed_from(self, command: Command) -> bool:
        return self.command != command

class StageOSCInput:
    def __init__(self, state: StageInputState, ip: str = "0.0.0.0", port: int = 1337, debug: bool = False) -> None:
        self.state = state
        self.internal_state = StageInputState()
        self.debug = debug
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/stop", self._osc_stop)
        self.dispatcher.map("/emergencystop", self._osc_emergencystop)
        self.dispatcher.map("/run*", self._osc_run)
        self.dispatcher.map("/mode", self._osc_mode)
        self.dispatcher.map("/speed", self._osc_speed)
        self.dispatcher.map("/direction", self._osc_direction)
        self.dispatcher.map("/angle", self._osc_angle)

        self.osc = ThreadingOSCUDPServer((ip, port), self.dispatcher)
        self.osc.timeout = 0.1

    def __call__(self):
        self.osc.handle_request()

    def _debug(self, msg: str) -> None:
        if self.debug:
            print("[OSC] %s" % msg)

    def _osc_stop(self, _: str, *__) -> None:
        self.state.action = Command.Action.STOP
        self._debug("Stop received")

    def _osc_emergencystop(self, _: str, *__) -> None:
        self.state.action = Command.Action.EMERGENCY_STOP
        self._debug("Emergency stop received")

    def _osc_run(self, addr: str, *osc_arguments) -> None:
        if addr == "/run":
            self.state.action = self.internal_state.action
        elif addr == "/run/continuous":
            self.state.action = Command.Action.RUN_CONTINUOUS
        elif addr == "/run/to_angle":
            self.state.action = Command.Action.RUN_TO_ANGLE
        else:
            self._debug("Invalid run address: %s" % addr)
            return
        self._debug("Start running (%s)" % self.state.action)

    def _osc_mode(self, _: str, *osc_arguments) -> None:
        if len(osc_arguments) != 1 and not isinstance(osc_arguments[0], str):
            self._debug("Invalid mode arguments: %s" % osc_arguments)
            return
        if osc_arguments[0] == "stop":
            self.internal_state.action == Command.Action.STOP
        elif osc_arguments[0] == "continuous":
            self.internal_state.action == Command.Action.RUN_CONTINUOUS
        elif osc_arguments[0] == "to_angle":
            self.internal_state.action == Command.Action.RUN_TO_ANGLE
        else:
            self._debug("Invalid mode: %s" % osc_arguments[0])
        self._debug("Set new mode: %s" % self.internal_state.action)

    def _osc_speed(self, addr: str, *osc_arguments) -> None:
        if len(osc_arguments) != 1 and not isinstance(osc_arguments[0], float):
            self._debug("Invalid speed arguments: %s" % osc_arguments)
            return
        self.internal_state.speed = osc_arguments[0]
        self.state.speed = osc_arguments[0]
        self._debug("Set new speed: %.2f" % self.state.speed)

    def _osc_direction(self, addr: str, *osc_arguments) -> None:
        if len(osc_arguments) != 1 and not isinstance(osc_arguments[0], str):
            self._debug("Invalid direction arguments: %s" % osc_arguments)
            return
        if osc_arguments[0].lower() == "clockwise":
            direction = Command.Direction.CLOCKWISE
        elif osc_arguments[0].lower() == "counterclockwise":
            direction = Command.Direction.COUNTERCLOCKWISE
        else:
            self._debug("Invalid direction: %s" % osc_arguments[0])
            return
        self.internal_state.direction = direction
        self.state.direction = direction
        self._debug("Set new direction: %s" % self.state.direction)

    def _osc_angle(self, addr: str, *osc_arguments) -> None:
        if len(osc_arguments) != 1 and not isinstance(osc_arguments[0], float):
            self._debug("Invalid angle arguments: %s" % osc_arguments)
            return
        if osc_arguments[0] < 0 or osc_arguments[0] >= 360:
            self._debug("Invalid new angle: %.2f" % osc_arguments[0])
            return
        self.internal_state.angle = osc_arguments[0]
        self.state.angle = osc_arguments[0]
        self._debug("Set new angle: %.2f" % self.state.angle)