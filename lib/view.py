from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple
import time
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

from .process import RuntimeEnvironment
from .runtime import Runtime
from .process import GenericProcess
from .stage.commands import Command


class ViewRuntime(Runtime):
    def __init__(self, commands: Connection) -> None:
        super().__init__()        

        # Connections
        self.commands = commands

        # Function classes
        self.osc: ThreadingOSCUDPServer = None

        # State
        self.active_command = Command(Command.Action.STOP)
        self.direction: Command.Direction = Command.Direction.CLOCKWISE
        self.speed: float = 1.0
        self.angle: float = 0.0
        self.command_changed = False

    def setup(self):
        dispatcher = Dispatcher()
        dispatcher.map("/stop", self.osc_set_stop)
        dispatcher.map("/run/*", self.osc_set_run)
        dispatcher.map("/direction", self.osc_set_direction)

        self.osc = ThreadingOSCUDPServer(("0.0.0.0", 1337), dispatcher)
        self.osc.timeout = 0.1

    def loop(self):
        self.osc.handle_request()

        if self.command_changed:
            self.commands.send(self.active_command)
            self.command_changed = False

    def stop(self) -> int | None:
        pass

    def set_new(self, cmd: Command) -> None:
        self.active_command = cmd
        self.command_changed = True

    def osc_set_stop(self, address: str, *osc_arguments) -> None:
        if self.active_command.is_run():
            self.set_new(Command(Command.Action.STOP))

    def osc_set_run(self, address: str, *osc_arguments) -> None:
        if address == "/run/to_angle":
            self.set_new(Command(Command.Action.RUN_TO_ANGLE, self.direction, self.speed, self.angle))
        elif address == "/run/continuous":
            self.set_new(Command(Command.Action.RUN_CONTINUOUS, self.direction, self.speed))

    def osc_set_direction(self, address: str, *osc_arguments) -> None:
        if len(osc_arguments) != 1 and not isinstance(osc_arguments[0], str):
            return
        if osc_arguments[0].lower() == 'clockwise':
            self.direction = Command.Direction.CLOCKWISE
        elif osc_arguments[0].lower() == 'counterclockwise':
            self.direction = Command.Direction.COUNTERCLOCKWISE
        else:
            return

class View(GenericProcess):
    def __init__(self) -> None:
        super().__init__()

    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        signal, runtime_signal = Pipe()
        self.commands, runtime_commands = Pipe()
        kwargs = {
            "commands": runtime_commands
        }
        return RuntimeEnvironment(ViewRuntime, runtime_signal, kwargs=kwargs), signal
