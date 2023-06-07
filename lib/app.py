import configparser
from typing import Iterable

from .process import GenericProcess, Message, Signals

class App:
    def __init__(self, debug: bool, testing: bool):
        self._shutdown = False
        self._config = configparser.ConfigParser()
        self._config['DEFAULT']['debug'] = str(debug)
        self._config['DEFAULT']['testing'] = str(testing)

    @property
    def shutdown(self) -> bool:
        return self._shutdown
    
    @property
    def is_debug_enabled(self) -> bool:
        return self._config.getboolean('DEFAULT', 'debug', fallback=False)
    
    @property
    def is_testing_enabled(self) -> bool:
        return self._config.getboolean('DEFAULT', 'testing', fallback=False)
    
    def exit(self) -> None:
        self._shutdown = True

    def read_config(self, filenames: str | Iterable[str]) -> None:
        self._config.read(filenames)

    def send_config_to(self, proc: GenericProcess, msg: Message) -> None:
        assert msg.signal == Signals.CONFIG, "Expect config message"
        assert isinstance(msg.data, tuple) and len(msg.data) == 3, "Expect tuple of length 3 with section and option and type"
        
        res = None
        if msg.data[0] not in self._config or msg.data[1] not in self._config[msg.data[0]]:
            print("Requested config [%s].%s does not exists" % (msg.data[0], msg.data[1]))  
        elif msg.data[2] == int:
            res = self._config.getint(msg.data[0], msg.data[1], fallback=None)
        elif msg.data[2] == bool:
            res = self._config.getboolean(msg.data[0], msg.data[1], fallback=None)
        elif msg.data[2] == float:
            res = self._config.getfloat(msg.data[0], msg.data[1], fallback=None)
        else:
            res = self._config.get(msg.data[0], msg.data[1], fallback=None)
        
        Message.config_signal_response(msg.data[0], msg.data[1], res).send_on(proc.signal)

