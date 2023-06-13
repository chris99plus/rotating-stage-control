from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple
import time

from .process import RuntimeEnvironment
from .runtime import Runtime, App
from .process import GenericProcess
from .stage.commands import Command
from .stage.input import StageInputState, StageOSCInput

class ViewRuntime(Runtime):
    def __init__(self, commands: Connection, app: App) -> None:
        super().__init__()
        self.app = app     

        # Connections
        self.commands = commands

        # Function classes
        self.state: StageInputState = None
        self.osc: StageOSCInput = None

        # State
        self.active_command = Command(Command.Action.STOP)

    def setup(self):
        self.state = StageInputState()
        self.osc = StageOSCInput(self.state, 
            self.app.get_config('input', 'ip', str, '0.0.0.0'),
            self.app.get_config('input', 'port', int, 1337),
            self.app.is_debug_enabled)

    def loop(self):
        self.osc()

        if self.state.changed_from(self.active_command):
            self.active_command = self.state.command
            self.commands.send(self.active_command)

        while self.commands.poll():
            active_command = self.commands.recv()
            assert isinstance(active_command, Command)
            print("Received active command different from current")

    def stop(self) -> int | None:
        pass
    
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
