from typing import List, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

class ExitCodes(Enum):
    """Exit codes describe the reason why a runtime exited"""
    SUCCESS = 0
    INIT_ERROR = 1
    RUNTIME_ERROR = 2
    SHUTDOWN_ERROR = 3

class Runtime(ABC):
    """Recurring tasks with great importance or high computational costs run in
    their own runtime, which itself runs in a seperate process. This runtime is
    split into three parts: Setup, loop and stop (or cleanup). Setup and stop
    are called once and loop is called repeatably until the runtime is forced to
    stop. The runtime object can be initialized with arguments."""
    @abstractmethod
    def setup():
        pass

    @abstractmethod
    def loop():
        pass

    @abstractmethod
    def stop() -> int | None:
        pass