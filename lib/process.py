from multiprocessing import Process
from multiprocessing.connection import Connection
from typing import Type, cast, Dict, Any, List, Tuple, Callable
from abc import ABC, abstractmethod
from enum import Enum
import traceback
import inspect
import time

from .runtime import Runtime, ExitCodes, App

class Signals(Enum):
    """Signal send to and from a process to communicate its state or call for
    action."""
    INITIALIZED = 0
    STOP = 1
    ERROR = 2
    CONFIG = 3
    DATA = 4

class Message:
    """Message between processes. Mainly focused on the communication between
    the main and child processes."""
    def __init__(self, frame: tuple[Signals, Any]) -> None:
        self.frame = frame

    @property
    def signal(self) -> Signals:
        return self.frame[0]
    
    @property
    def data(self) -> Any:
        return self.frame[1]
    
    def send_on(self, c: Connection) -> None:
        c.send(self.frame)

    @staticmethod
    def recv_from(c: Connection) -> 'Message':
        frame = c.recv()
        assert isinstance(frame, tuple), "Message expected a tuple, but got %s" % type(frame)
        assert len(frame) == 2, "Expected a tuple with 2 elements, actual length is %i" % len(frame)
        return Message(frame)

    @staticmethod
    def initialized_signal() -> 'Message':
        return Message((Signals.INITIALIZED, None))

    @staticmethod
    def stop_signal() -> 'Message':
        return Message((Signals.STOP, None))
    
    @staticmethod
    def error_signal(e: Exception | None = None) -> 'Message':
        return Message((Signals.ERROR, str(e)))
    
    @staticmethod
    def config_signal(section: str, option: str, t: Type) -> 'Message':
        return Message((Signals.CONFIG, (section, option, t)))
    
    @staticmethod
    def config_signal_response(section: str, option: str, data: Any) -> 'Message':
        return Message((Signals.CONFIG, (section, option, data)))

    @staticmethod
    def data_signal(d: Any) -> 'Message':
        return Message((Signals.DATA, d))
    
class AppProxy(App):
    def __init__(self, signal: Connection) -> None:
        super().__init__()
        self.signal = signal
        self.config = {}

    def send(self, data: Any) -> None:
        Message.data_signal(data).send_on(self.signal)

    def get_config(self, section: str, option: str, t: Type = str, default: Any = None, timeout: float = 2.0) -> Any:
        Message.config_signal(section, option, t).send_on(self.signal)
        if self.signal.poll(timeout):
            ans = Message.recv_from(self.signal)
            assert ans.signal == Signals.CONFIG, ("Expected config signal. Got %s" % ans.signal)
            assert isinstance(ans.data, tuple) and len(ans.data) == 3, "Expected tuple response of length 3"
            assert ans.data[0] == section or ans.data[1] == option, (
                "Config section or option does not match in the response. Got [%s].%s" % (ans.data[0], ans.data[1]))
            if ans.data[2] is None:
                return default
            else:
                return ans.data[2]
        raise Exception("Failed to get config value %s.%s" % (section, option))

    def setup(self) -> None:
        self.config['debug'] = self.get_config('DEFAULT', 'debug', bool)
        self.config['testing'] = self.get_config('DEFAULT', 'testing', bool)

    @property
    def is_testing_enabled(self) -> bool:
        return self.config['testing'] == True
    
    @property
    def is_debug_enabled(self) -> bool:
        return self.config['debug'] == True

class RuntimeEnvironment(Process):
    """Python Process which contains a runtime and controls the runtime lifecycle."""
    def __init__(self, runtime_cls: Type[Runtime],
                 signal: Connection, args: List[Any] = [],
                 kwargs: Dict[str, Any] = {}, min_loop_duration: int = 5) -> None:
        super().__init__(args=args, kwargs={"runtime_cls": runtime_cls, "signal": signal, "kwargs": kwargs})
        self.min_loop_duration = min_loop_duration

    def run(self):
        """Run method is executed inside the process and implements the runtime
        lifecycle. The lifecycle consists of these parts:
            1. Instantiate runtime object with arguments
            2. Call setup method of runtime
            3. Call loop method until STOP signal is received
            4. Call stop method of runtime
        """
        signal  = cast(Connection, self._kwargs["signal"])
        app_proxy = AppProxy(signal)

        r = cast(Type[Runtime], self._kwargs["runtime_cls"])
        runtime_init_sig = inspect.signature(r.__init__)

        if 'app' in runtime_init_sig.parameters and \
            isinstance(app_proxy, runtime_init_sig.parameters['app'].annotation):
            self._kwargs["kwargs"]['app'] = app_proxy

        runtime = cast(Type[Runtime], self._kwargs["runtime_cls"])(*self._args, **self._kwargs["kwargs"])
        min_duration_loop = self.min_loop_duration / 1000
        last_loop = time.time()

        # Runtime startup
        try:
            app_proxy.setup()
            runtime.setup()
        except Exception as e:
            print("[%s] %s%s" % (runtime.__class__.__name__, e.__class__.__name__, ": %s" % e if str(e) != "" else ""))
            print("[%s] %s" % (runtime.__class__.__name__, traceback.format_exc()))
            Message.error_signal(e).send_on(signal)
            exit(ExitCodes.INIT_ERROR.value)
        
        Message.initialized_signal().send_on(signal)
        
        # Runtime loop
        exitcode = ExitCodes.SUCCESS
        while True:
            if signal.poll() and Message.recv_from(signal).signal == Signals.STOP:
                break
            
            try:
                runtime.loop()
            except EOFError:
                # EOFError is usually triggered if another process fails and
                # closes its connections. The current process should try to live
                # with this situation and is probably be shutdown or restarted
                # by the main process. 
                time.sleep(0.5)
            except Exception as e:
                print("[%s] %s%s" % (runtime.__class__.__name__, e.__class__.__name__, ": %s" % e if str(e) != "" else ""))
                print("[%s] %s" % (runtime.__class__.__name__, traceback.format_exc()))
                Message.error_signal(e).send_on(signal)
                exitcode = ExitCodes.RUNTIME_ERROR
                break

            # The CPU of the PI is blocked by all the loop. Further the loop is
            # stopped if it does nothing and is to fast.
            loop_duration = time.time() - last_loop
            if loop_duration < min_duration_loop:
                time.sleep(min_duration_loop - loop_duration)
            last_loop = time.time()

        # Runtime shutdown
        try:
            stop_returncode = runtime.stop()
        except Exception as e:
            print("[%s] %s%s" % (runtime.__class__.__name__, e.__class__.__name__, ": %s" % e if str(e) != "" else ""))
            print("[%s] %s" % (runtime.__class__.__name__, traceback.format_exc()))
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

    def start(self, config_callback: Callable[['GenericProcess', Message], None], timeout: int = 30) -> None:
        """Start the runtime"""
        if self._process is not None:
            return
        self._process, self._signal = self.init()
        self.process.start()

        starting = True
        initialized = False
        init_started = time.time()
        while starting:
            msg = self.recv()
            if msg is not None and msg.signal == Signals.INITIALIZED:
                initialized = True
                starting = False
            elif msg is not None and msg.signal == Signals.CONFIG:
                config_callback(self, msg)

            if time.time() - init_started > timeout:
                starting = False
        if not initialized:
            self.stop()
            raise Exception("Initializing process %s failed." % self.__class__.__name__)

    def stop(self, timeout: int = 5) -> int | None:
        """Stops the runtime"""
        if self._process is None:
            return
        
        try:
            Message.stop_signal().send_on(self.signal)
        except BrokenPipeError:
            print("Pipe broke while trying to stop %s. Continue with process shutdown." % self.__class__.__name__)
        
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.kill()
            print("Timeout exceeded while stopping %s. It was forced to quit!" % self.__class__.__name__)
        exitcode = self.process.exitcode
        self._process = None
        return exitcode
    
    def restart(self, config_callback: Callable[['GenericProcess', Message], None], timeout: int = 5):
        """Restarts the runtime. Dependent processes are restarted as well, to
        ensure the functionality of shared pipes. Be aware, that only directly
        connected processes are restarted."""
        self.stop(timeout)
        [p.stop() for p in self._subscriber]
        self.start(config_callback)
        [p.start(config_callback) for p in self._subscriber]
    
    def recv(self) -> Message | None:
        """Return app signal if a new signal is available"""
        if self.signal.poll():
            return Message.recv_from(self.signal)
        else:
            return None