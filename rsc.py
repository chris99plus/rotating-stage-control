from lib.app import App, Signals
from lib.control import Control
from lib.sensors import AbsoluteSensor
from lib.view import View
from lib.utility.plot import init_graphs, update_graphs, append_rotation_data
import signal
import math
import argparse
import traceback

def graceful_shutdown(_, __):
    global app
    app.exit()

def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='rsc')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--testing', action='store_true')
    return parser.parse_args()

def loop_view(view: View):
    msg = view.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            view.restart(app.send_config_to)
        elif msg.signal == Signals.CONFIG:
            app.send_config_to(view, msg)

def loop_control(control: Control):
    msg = control.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            control.restart(app.send_config_to)
        elif msg.signal == Signals.DATA:
            assert isinstance(msg.data, tuple)
            if app.is_debug_enabled:
                append_rotation_data(math.radians(msg.data[0]), msg.data[1])
        elif msg.signal == Signals.CONFIG:
            app.send_config_to(control, msg)

def loop_absolute_sensor(absolute_sensor: AbsoluteSensor):
    msg = absolute_sensor.recv()
    if msg is not None:
        if msg.signal == Signals.ERROR:
            absolute_sensor.restart(app.send_config_to)
        elif msg.signal == Signals.CONFIG:
            app.send_config_to(absolute_sensor, msg)

def main(args: argparse.Namespace):
    global app
    app = App(args.debug, args.testing)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # Initialization
    # Processes are initialized and started. If something fails,
    # the whole application should be closed. 
    view = View()
    absolute_sensor = AbsoluteSensor()
    control = Control(view, absolute_sensor)

    try:
        absolute_sensor.start(app.send_config_to)
        view.start(app.send_config_to)
        control.start(app.send_config_to)
    except Exception as e:
        print("Failed to initialize app!")
        print("[ERROR] %s" % str(e))
        print(traceback.format_exc())
        app.exit()

    # Loop
    try:
        if app.is_debug_enabled:
            init_graphs()

        while not app.shutdown:
            if app.is_debug_enabled:
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