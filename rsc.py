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

def main(args: argparse.Namespace):
    global shutdown
    global debug
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    debug = args.debug

    view = View()
    absolute_sensor = AbsoluteSensor()
    control = Control(view, absolute_sensor)

    try:
        absolute_sensor.start()
        view.start()
        control.start()
    except:
        shutdown = True

    try:
        if debug:
            init_graphs()

        while not shutdown:
            if debug:
                update_graphs()
            
            csmsg = control.recv()
            if csmsg is not None:
                if csmsg.signal == Signals.ERROR:
                    control.restart()
                elif csmsg.signal == Signals.DATA:
                    assert isinstance(csmsg.data, tuple)
                    append_rotation_data(csmsg.data[0], csmsg.data[1])
            
            asmsg = absolute_sensor.recv()
            if asmsg is not None:
                if asmsg.signal == Signals.ERROR:
                    absolute_sensor.restart()

            vmsg = view.recv()
            if vmsg is not None:
                if vmsg.signal == Signals.ERROR:
                    view.restart()
    finally:
        print(f"... Received signal. Shutting down ...")
        print("Control exited with %s" % control.stop())
        print("Absolute sensor exited with %s" % absolute_sensor.stop())
        print("View exited with %s" % view.stop())

if "__main__" == __name__:
    main(args())