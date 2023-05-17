from lib import Signals, Control, AbsoluteSensor
import signal

shutdown = False

def graceful_shutdown(_, __):
    global shutdown
    shutdown = True

def main():
    global shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    absolute_sensor = AbsoluteSensor()
    control = Control(absolute_sensor)

    absolute_sensor.start()
    control.start()

    while not shutdown:
        csignal = control.recv_signal()
        if csignal is not None:
            if csignal == Signals.ERROR:
                control.restart()
        
        assignal = absolute_sensor.recv_signal()
        if assignal is not None:
            if assignal == Signals.ERROR:
                absolute_sensor.restart()

    print(f"... Received signal. Shutting down ...")
    print("Control exited with %i" % control.stop())
    print("Absolute sensor exited with %i" % absolute_sensor.stop())

if "__main__" == __name__:
    main()