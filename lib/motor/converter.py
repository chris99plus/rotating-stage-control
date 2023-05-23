import minimalmodbus
from abc import ABC, abstractmethod

class FrequencyConverter(ABC):
    @abstractmethod
    def set_target_frequency(self, frequency: float) -> None:
        pass

    @abstractmethod
    def get_target_frequency(self) -> float:
        pass

    @abstractmethod
    def get_current_frequency(self) -> float:
        pass

    @abstractmethod
    def run(self, forward: bool) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def emergency_stop(self) -> None:
        pass

class JSLSM100Converter(FrequencyConverter):
    """Read and writes Parameters to the frequency converter"""
    def __init__(self, converter_address: int, port: str = '/dev/ttyUSB1') -> None:
        super().__init__()
        self.jslsm100 = minimalmodbus.Instrument(port, converter_address, mode=minimalmodbus.MODE_RTU)

    def set_target_frequency(self, frequency: float) -> None:
        self.jslsm100.write_register(int('0x0005', 0), int(round(frequency, 2) / 0.01), functioncode=6)

    def get_target_frequency(self) -> float:
        return self.jslsm100.read_register(int('0x0005', 0), functioncode=3) * 0.01
    
    def get_current_frequency(self) -> float:
        return self.jslsm100.read_float(int('0x000A', 0), functioncode=3) * 0.01
    
    def run(self, forward: bool) -> None:
        run_value = int('B1', 16) if forward else int('B2', 16)
        self.jslsm100.write_register(int('0x0006', 0), run_value, functioncode=6)

    def stop(self) -> None:
        self.jslsm100.write_register(int('0x0006', 0), int('B0', 16), functioncode=6)

    def emergency_stop(self) -> None:
        self.jslsm100.write_register(int('0x0006', 0), int('B4', 16), functioncode=6)