from multiprocessing.connection import Connection
from multiprocessing import Pipe
from typing import Any, Dict, List, Tuple, cast
import cv2
import time
import math

from .runtime import Runtime
from .process import GenericProcess, BaseProcess

class AbsoluteSensorRuntime(Runtime):
    def __init__(self, args: List[Any], kwargs: Dict[str, Any]) -> None:
        super().__init__(args, kwargs)
        self.values = cast(Connection, self.kwargs["values"])
        self.camera = 0

    def setup(self) -> None:
        # Define the ArUco dictionary and parameters
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
        self.aruco_params = cv2.aruco.DetectorParameters()
        # Initialize the camera capture
        self.cap = cv2.VideoCapture(self.camera)

    def calculate_angle(self, vector1, vector2):
        angle_radians = math.atan2(vector2[1], vector2[0]) - math.atan2(vector1[1], vector1[0])
        angle_degrees = math.degrees(angle_radians)

        # Adjust the angle to be within the range of 0 to 360 degrees
        #angle_degrees %= 360
        return angle_degrees

    def get_angele(self, aruco_dict, aruco_params, cap, number_of_tracker, debug=False):
        # Read a frame from the camera
        _, frame = cap.read()

        angel_dif = 360 / number_of_tracker

        # todo: make it variable in amount of tracker (n > 4 )

        # Detect ArUco markers in the frame
        detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        corners, ids, _ = detector.detectMarkers(frame)
        angle_count = 0
        # If a marker was detected, calculate its rotation
        if ids is not None:
            for index, i in enumerate(corners):
                translated_corners = i[0]

                vector_rectangel = translated_corners[0] - translated_corners[1]
                vector_base = [0, 1]
                angle = self.calculate_angle(vector_rectangel, vector_base)
                
                ids_tmp = ids[index][0]

                #tracker start with ID 1
            
                angle -= angel_dif * (ids_tmp)

                angle %= 360
                angle_count += angle
            caluclated_angle = angle_count / len(ids)
        else:
            caluclated_angle = -1

        return caluclated_angle

    def loop(self) -> None:
        # laufmessung
        start = time.time()

        caluclated_angle = self.get_angele(self.aruco_dict, self.aruco_params, self.cap, number_of_tracker=4, debug=False)
        if caluclated_angle >= 0:
            self.values.send(caluclated_angle)

        # laufmessung
        end = time.time()

    def stop(self) -> int | None:
        self.cap.release()

class AbsoluteSensor(GenericProcess):
    def __init__(self) -> None:
        super().__init__()

    def init(self) -> Tuple[BaseProcess, Connection]:
        signal, runtime_signal = Pipe()
        self.values, runtime_value = Pipe()
        kwargs = {
            "values": runtime_value
        }
        return BaseProcess(AbsoluteSensorRuntime, runtime_signal, kwargs=kwargs), signal
