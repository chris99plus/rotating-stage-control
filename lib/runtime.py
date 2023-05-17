from typing import List, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

class ExitCodes(Enum):
    SUCCESS = 0
    INIT_ERROR = 1
    RUNTIME_ERROR = 2

class Runtime(ABC):
    def __init__(self, args: List[Any], kwargs: Dict[str, Any]) -> None:
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def setup():
        pass

    @abstractmethod
    def loop():
        pass

    @abstractmethod
    def stop() -> int | None:
        pass