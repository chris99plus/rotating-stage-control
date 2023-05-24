from typing import Any
from abc import ABC, abstractmethod
from enum import Enum

class ExitCodes(Enum):
    """Exit codes describe the reason why a runtime exited"""
    SUCCESS = 0
    INIT_ERROR = 1
    RUNTIME_ERROR = 2
    SHUTDOWN_ERROR = 3

class App(ABC):
    """Representation of the main process inside the child process. An object of
    this class is passed to the child process, if the runtime constructor has an
    app argument."""
    @abstractmethod
    def send(self, data: Any) -> None:
        pass

class Runtime(ABC):
    """Recurring tasks with great importance or high computational costs run in
    their own runtime, which itself runs in a seperate process. This runtime is
    split into three parts: Setup, loop and stop (or cleanup). Setup and stop
    are called once and loop is called repeatably until the runtime is forced to
    stop. The runtime is initialized with arguments passed to the class
    constructor."""
    @abstractmethod
    def setup():
        pass

    @abstractmethod
    def loop():
        pass

    @abstractmethod
    def stop() -> int | None:
        pass