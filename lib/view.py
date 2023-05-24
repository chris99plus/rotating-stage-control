from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Tuple

from lib.process import RuntimeEnvironment
from .runtime import Runtime
from .process import GenericProcess
from .stage.commands import Command

import time

class ViewRuntime(Runtime):
    def __init__(self, commands: Connection) -> None:
        super().__init__()
        self.commands = commands
        self.send = False

    def setup(self):
        pass

    def loop(self):
        if not self.send:
            time.sleep(5)
            self.commands.send(Command(Command.Action.RUN_TO_ANGLE, Command.Direction.CLOCKWISE, 1, 90.0))
            self.send = True

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
