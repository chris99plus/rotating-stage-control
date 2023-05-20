from multiprocessing import Process
from multiprocessing.connection import Connection
from typing import Type, cast, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import traceback

from .runtime import Runtime, ExitCodes

class Signals(Enum):
    """Signal send to and from a process to communicate its state or call for
    action."""
    INITIALIZED = 0
    STOP = 1
    ERROR = 2

class RuntimeEnvironment(Process):
    """Python Process which contains a runtime and controls the runtime lifecycle."""
    def __init__(self, runtime_cls: Type[Runtime],
                 signal: Connection, args: List[Any] = [], kwargs: Dict[str, Any] = {}) -> None:
        super().__init__(args=args, kwargs={"runtime_cls": runtime_cls, "signal": signal, "kwargs": kwargs})

    def run(self):
        """Run method is executed inside the process and implements the runtime
        lifecycle. The lifecycle consists of these parts:
            1. Instantiate runtime object with arguments
            2. Call setup method of runtime
            3. Call loop method until STOP signal is received
            4. Call stop method of runtime
        """
        signal  = cast(Connection, self._kwargs["signal"])
        runtime = cast(Type[Runtime], self._kwargs["runtime_cls"])(*self._args, **self._kwargs["kwargs"])

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
                e.__traceback__
                print("[%s] %s%s" % (runtime.__class__.__name__, e.__class__.__name__, ": %s" % e if str(e) != "" else ""))
                print("[%s] %s" % (runtime.__class__.__name__, traceback.format_exc()))
                signal.send(Signals.ERROR)
                exitcode = ExitCodes.RUNTIME_ERROR
                break

        # Runtime shutdown
        try:
            stop_returncode = runtime.stop()
        except Exception:
            exit(ExitCodes.SHUTDOWN_ERROR)
        
        if stop_returncode is not None:
            exit(stop_returncode + list(ExitCodes.__members__.values())[-1].value)
        else:
            exit(exitcode.value)

class GenericProcess(ABC):
    """A wrapper for RuntimeEnvironment with process control functions"""
    def __init__(self) -> None:
        super().__init__()
        self._process: RuntimeEnvironment | None = None
        self._signal: Connection | None = None
        self._subscriber = set[GenericProcess]()

    @property
    def process(self) -> RuntimeEnvironment:
        assert self._process is not None
        return self._process

    @property
    def signal(self) -> Connection:
        assert self._signal is not None
        return self._signal

    @abstractmethod
    def init(self) -> Tuple[RuntimeEnvironment, Connection]:
        """Initializes runtime objects as it is required by the specific process
        and returns the RuntimeEnvironment object and the app signal pipe.
        Everytime this method is called new objects need to be created.
        Otherwise, pipes and other functions could be closed and fail."""

    def depends(self, process: 'GenericProcess') -> None:
        """Defines the dependency to another process."""
        process._subscriber.add(self)

    def start(self, timeout: int = 30) -> None:
        """Start the runtime"""
        if self._process is not None:
            return
        self._process, self._signal = self.init()
        self.process.start()
        if self._signal.poll(timeout) and self.recv_signal() == Signals.INITIALIZED:
            return
        else:
            self.stop()
            raise Exception("Initializing process %s failed." % self.__class__.__name__)

    def stop(self, timeout: int = 5) -> int | None:
        """Stops the runtime"""
        try:
            self.signal.send(Signals.STOP)
        except BrokenPipeError:
            print("Pipe broke while trying to stop %s. Continue with process shutdown." % self.__class__.__name__)
        
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.kill()
            print("Timeout exceeded while stopping %s. It was forced to quit!" % self.__class__.__name__)
        exitcode = self.process.exitcode
        self._process = None
        return exitcode
    
    def restart(self, timeout: int = 5):
        """Restarts the runtime. Dependent processes are restarted as well, to
        ensure the functionality of shared pipes. Be aware, that only directly
        connected processes are restarted."""
        self.stop(timeout)
        [p.stop() for p in self._subscriber]
        self.start()
        [p.start() for p in self._subscriber]
    
    def recv_signal(self) -> Signals | None:
        """Return app signal if a new signal is available"""
        if self.signal.poll():
            return self.signal.recv()
        else:
            return None