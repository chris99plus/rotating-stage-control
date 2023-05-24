from lib import Signals, Control, AbsoluteSensor, View
from lib.utility.plot import init_graphs, update_graphs, append_rotation_data
import signal
import argparse

shutdown = False
debug = False

def graceful_shutdown(_, __):
    global shutdown
    shutdown = True

def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='rsc')
    parser.add_argument('-d', '--debug', action='store_true')
    return parser.parse_args()

def loop_view(view: View):
    msg = view.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            view.restart()

def loop_control(control: Control):
    msg = control.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            control.restart()
        elif msg.signal == Signals.DATA:
            assert isinstance(msg.data, tuple)
            append_rotation_data(msg.data[0], msg.data[1])

def loop_absolute_sensor(absolute_sensor: AbsoluteSensor):
    msg = absolute_sensor.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            absolute_sensor.restart()

def main(args: argparse.Namespace):
    global shutdown
    global debug
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    debug = args.debug

    # Initialization
    # Processes are initialized and started. If something fails,
    # the whole application should be closed. 
    view = View()
    absolute_sensor = AbsoluteSensor()
    control = Control(view, absolute_sensor)

    try:
        absolute_sensor.start()
        view.start()
        control.start()
    except:
        shutdown = True

    # Loop
    try:
        if debug:
            init_graphs()

        while not shutdown:
            if debug:
                update_graphs()
            loop_absolute_sensor(absolute_sensor)
            loop_view(view)
            loop_control(control)
    
    # Shutdown
    finally:
        print(f"... Received signal. Shutting down ...")
        print("Control exited with %s" % control.stop())
        print("Absolute sensor exited with %s" % absolute_sensor.stop())
        print("View exited with %s" % view.stop())

if "__main__" == __name__:
    main(args())