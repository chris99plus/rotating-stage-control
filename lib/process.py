from multiprocessing import Process
from multiprocessing.connection import Connection
from typing import Type, cast, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
from enum import Enum

from .runtime import Runtime, ExitCodes

class Signals(Enum):
    """Signal send to and from a process to communicate its state or call for
    action."""
    INITIALIZED = 0
    STOP = 1
    ERROR = 2

class RuntimeEnv(Process):
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
                print("[%s] Exception: %s" % (runtime.__class__.__name__, e))
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
        self._process: RuntimeEnv | None = None
        self._signal: Connection | None = None
        self._subscriber = set[GenericProcess]()

    @property
    def process(self) -> RuntimeEnv:
        assert self._process is not None
        return self._process

    @property
    def signal(self) -> Connection:
        assert self._signal is not None
        return self._signal

    @abstractmethod
    def init(self) -> Tuple[RuntimeEnv, Connection]:
        pass

    def depends(self, process: 'GenericProcess') -> None:
        process._subscriber.add(self)

    def start(self) -> None:
        if self._process is not None:
            return
        self._process, self._signal = self.init()
        self.process.start()

    def stop(self, timeout: int = 5) -> int | None:
        self.signal.send(Signals.STOP)
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.kill()
            print("Timeout exceeded while stopping %s. It was forced to quit!" % self.__class__.__name__)
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
            return self.signal.recv()
        else:
            return None