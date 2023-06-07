# rotating-stage-control

## Requirements
- Processing of input commands
- Send commands to motor controller
- Analyse absolute position of rotation stage with a camera and ArUco markers
- Check state of motor converter (manuel/remote, emergency stop, errors)
- Implement safety mechanisms (watchdogs, sanity checks, cycle time, ...)
- Remote control parameters:
    - Angle / Continuous mode
    - Destination angle
    - Speed
    - Direction

## Architecture
### Threads
- Command
    - External API endpoint
    - (OSC)
    - (Websocket)
- Sensor
    - Angle
    - FPS
    - Accuracy
- Control
    - motor converter commands
    - motor converter states
    - Calculate motor commands
- Main
    - Global state
    - Watchdogs

## Algorithm
Optical sensor is required to specify the time, when the last value was
calculated. The current angle can be calculated using the current speed and the
time since the last update. The speed can be calculated with the last measured
angles. One angle calculation should not need more then 33.3 ms to complete to
get 30 fps or 16.6 ms for 60 fps.