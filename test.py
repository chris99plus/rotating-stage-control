from lib.stage.motor import JSLSM100Converter
import time

if __name__ == "__main__":
    motor = JSLSM100Converter(1)
    print("Motor Converter JSLSM100")
    print("========================")
    print("  Version %s.%s" % motor.version())
    print("")
    
    while True:
        print("  State: %s" % motor.get_state())
        print("  Power: %s kW" % motor.get_power())
        print("  Frequency (current, target): %.2f, %.2f" % ( motor.get_current_frequency(), motor.get_target_frequency()))
        time.sleep(0.5)