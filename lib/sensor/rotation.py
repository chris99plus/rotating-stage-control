from typing import Any
from abc import ABC, abstractmethod
import cv2
import math

class RotationSensor(ABC):
    def init(self) -> None:
        return
    
    def release(self) -> None:
        return

    @abstractmethod
    def measure_angle(self) -> float | None:
        pass

class OpticalRotationSensor(RotationSensor):
    def __init__(self, camera: int = 0, number_of_tracker: int = 36, ) -> None:
        super().__init__()
        self.camera = camera
        self.number_of_tracker = number_of_tracker
        self.aruco_dict: Any = None
        self.aruco_params: Any = None
        self.cap: cv2.VideoCapture = None

    def init(self) -> None:
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

    def measure_angle(self) -> float | None:
        # Read a frame from the camera
        _, frame = self.cap.read()
        angel_dif = 360 / self.number_of_tracker

        # Detect ArUco markers in the frame
        detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
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
            
                angle -= angel_dif * (ids_tmp)

                angle %= 360
                angle_count += angle
            return angle_count / len(ids)
        else:
            return None

    def release(self) -> None:
        self.cap.release()