from lib import Signals, Control, AbsoluteSensor, View
import signal

shutdown = False

def graceful_shutdown(_, __):
    global shutdown
    shutdown = True

def main():
    global shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    view = View()
    absolute_sensor = AbsoluteSensor()
    control = Control(view, absolute_sensor)

    try:
        absolute_sensor.start()
        view.start()
        control.start()
    except:
        shutdown = True

    while not shutdown:
        csignal = control.recv_signal()
        if csignal is not None:
            if csignal == Signals.ERROR:
                control.restart()
        
        assignal = absolute_sensor.recv_signal()
        if assignal is not None:
            if assignal == Signals.ERROR:
                absolute_sensor.restart()

        vsignal = view.recv_signal()
        if vsignal is not None:
            if vsignal == Signals.ERROR:
                view.restart()

    print(f"... Received signal. Shutting down ...")
    print("Control exited with %s" % control.stop())
    print("Absolute sensor exited with %s" % absolute_sensor.stop())
    print("View exited with %s" % view.stop())

if "__main__" == __name__:
    main()