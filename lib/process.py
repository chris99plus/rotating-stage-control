from multiprocessing import Process
from multiprocessing.connection import Connection
from typing import Type, cast, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
from enum import Enum

from .runtime import Runtime, ExitCodes

class Signals(Enum):
    INITIALIZED = 0
    STOP = 1
    ERROR = 2

class State(Enum):
    INITIALIZING = 0
    RUNNING = 1
    STOPPING = 2
    FINISHED = 3

class BaseProcess(Process):
    def __init__(self, runtime_cls: Type[Runtime],
                 signal: Connection, args: List[Any] = [], kwargs: Dict[str, Any] = {}) -> None:
        super().__init__(args=args, kwargs={"runtime_cls": runtime_cls, "signal": signal, "kwargs": kwargs})

    def run(self):
        signal  = cast(Connection, self._kwargs["signal"])
        runtime = cast(Type[Runtime], self._kwargs["runtime_cls"])(self._args, self._kwargs["kwargs"])

        # Runtime startup
        try:
            runtime.setup()
        except:
            signal.send(Signals.ERROR)
            exit(ExitCodes.INIT_ERROR.value)
        signal.send(Signals.INITIALIZED)
        
        # Runtime loop
        exitcode = ExitCodes.SUCCESS
        while True:
            if signal.poll() and signal.recv() == Signals.STOP:
                break
            
            try:
                runtime.loop()
            except Exception as e:
                print(e)
                signal.send(Signals.ERROR)
                exitcode = ExitCodes.RUNTIME_ERROR
                break

        # Runtime shutdown
        stop_returncode = runtime.stop()
        if stop_returncode is not None:
            exit(stop_returncode + list(ExitCodes.__members__.values())[-1].value)
        else:
            exit(exitcode.value)

class GenericProcess(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._last_signal = None
        self._process: BaseProcess | None = None
        self._signal: Connection | None = None
        self._subscriber = set[GenericProcess]()

    @property
    def process(self) -> BaseProcess:
        assert self._process is not None
        return self._process

    @property
    def signal(self) -> Connection:
        assert self._signal is not None
        return self._signal

    @abstractmethod
    def init(self) -> Tuple[BaseProcess, Connection]:
        pass

    def depends(self, process: 'GenericProcess') -> None:
        process._subscriber.add(self)

    @property
    def state(self) -> State:
        if self._last_signal is None:
            return State.INITIALIZING
        elif self.process.is_alive() and self._last_signal == Signals.INITIALIZED:
            return State.RUNNING
        elif self.process.is_alive() and (self._last_signal == Signals.STOP or self._last_signal == Signals.ERROR):
            return State.STOPPING
        elif not self.process.is_alive():
            return State.FINISHED
        else:
            raise ValueError("Unknown state")

    def start(self) -> None:
        if self._process is not None:
            return
        self._process, self._signal = self.init()
        self.process.start()

    def stop(self, timeout: int = 5) -> int | None:
        self.signal.send(Signals.STOP)
        self._last_signal = Signals.STOP
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.kill()
        exitcode = self.process.exitcode
        self._process = None
        return exitcode
    
    def restart(self, timeout: int = 5):
        self.stop(timeout)
        [p.stop() for p in self._subscriber]
        self.start()
        [p.start() for p in self._subscriber]
    
    def recv_signal(self) -> Signals | None:
        if self.signal.poll():
            signal = self.signal.recv()
            self._last_signal = signal
            return signal
        else:
            return None