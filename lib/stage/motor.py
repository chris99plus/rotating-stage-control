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
    def __init__(self, converter_address: int, port: str = '/dev/serial0', debug: bool = False) -> None:
        super().__init__()
        self.jslsm100 = minimalmodbus.Instrument(port, converter_address, mode=minimalmodbus.MODE_RTU, debug=debug)

    def reg_addr(self, hex_addr: str) -> int:
        return int(hex_addr, 0) - 1
    
    def read_reg(self, hex_addr: str) -> int | float:
        return self.jslsm100.read_register(self.reg_addr(hex_addr), functioncode=3)

    def version(self) -> tuple[int, int]:
        version = self.read_reg('0x0003')
        return (version >> 8, version & 0x00ff)

    def set_target_frequency(self, frequency: float) -> None:
        self.jslsm100.write_register(int('0x0005', 0), int(round(frequency, 2) / 0.01), functioncode=6)

    def get_target_frequency(self) -> float:
        return self.read_reg('0x0005') * 0.01
    
    def get_current_frequency(self) -> float:
        return self.read_reg('0x000A') * 0.01
    
    def run(self, forward: bool) -> None:
        current = self.read_reg('0x0006')
        current = current & 0b1111111111100000

        run_value = 0b00010 if forward else 0b00100
        new_value = current + run_value
        self.jslsm100.write_register(self.reg_addr('0x0006'), new_value, functioncode=6)

    def stop(self) -> None:
        current = self.read_reg('0x0006')
        current = current & 0b1111111111100000

        new_value = current + 0b00001
        self.jslsm100.write_register(self.reg_addr('0x0006'), new_value, functioncode=6)

    def get_state(self) -> str:
        current = self.read_reg('0x000E')
        return "{0:b}".format(current)
    
    def get_power(self) -> float:
        return self.read_reg('0x0009') * 0.1

    def emergency_stop(self) -> None:
        self.jslsm100.write_register(int('0x0006', 0), int('B4', 16), functioncode=6)

class TestConverter(FrequencyConverter):
    def __init__(self) -> None:
        super().__init__()
        self.frequency = 0.0
        self.running = False
        self.emergency = False

    def set_target_frequency(self, frequency: float) -> None:
        self.frequency = frequency
        print("[Test Converter] Set target frequency to %.2f" % frequency)

    def get_target_frequency(self) -> float:
        return self.frequency

    def get_current_frequency(self) -> float:
        return self.frequency

    def run(self, forward: bool) -> None:
        self.running = True
        print("[Test Converter] Set run command! Run %s" % ("forwards" if forward else "backwards"))

    def stop(self) -> None:
        self.running = False
        print("[Test Converter] Set stop command!")

    def emergency_stop(self) -> None:
        self.running = False
        self.emergency = True
        print("[Test Converter] EMERGENCY STOP!!! Stopping immediately!")