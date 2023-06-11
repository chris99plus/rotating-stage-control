from typing import Any
from abc import ABC, abstractmethod
import cv2
import numpy as np
import math
from time import time

from lib.utility.angle import Angle

class RotationSensor(ABC):
    def init(self) -> None:
        return
    
    def release(self) -> None:
        return
    
    @property
    @abstractmethod
    def last_angle(self) -> Angle | None:
        pass

    @property
    @abstractmethod
    def last_angle_recording() -> float | None:
        pass

    @abstractmethod
    def measure_angle(self) -> Angle | None:
        pass

class OpticalRotationSensor(RotationSensor):
    def __init__(self, camera: int = 0, number_of_tracker: int = 36, debug: bool = False) -> None:
        super().__init__()
        self.debug = debug
        self.camera = camera
        self.number_of_tracker = number_of_tracker
        self.aruco_dict: Any = None
        self.aruco_params: Any = None
        self.cap: cv2.VideoCapture = None
        self._last_angle: Angle | None = None
        self._last_angle_recording: float | None = None

    @property
    def last_angle(self) -> Angle | None:
        return self._last_angle
    
    @property
    def last_angle_recording(self) -> float | None:
        return self._last_angle_recording

    def init(self) -> None:
        # Define the ArUco dictionary and parameters
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        # Initialize the camera capture
        self.cap = cv2.VideoCapture(self.camera)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

    def average_angle(self, angle1, angle2):
        # Calculate the average of two angles considering the wrapping around case
        diff = (angle2 - angle1 + np.pi) % (2 * np.pi) - np.pi
        return (angle1 + diff / 2) % (2 * np.pi)

    def calculate_median_angle(self, angles):
        angles_in_radians = np.radians(angles)
        sorted_angles = np.sort(angles_in_radians)
        num_angles = len(sorted_angles)            

        if num_angles % 2 == 1:
            # If there are odd number of angles, return the middle angle
            median_angle = np.degrees(sorted_angles[num_angles // 2])
        else:
            # If there are even number of angles, return the average of the two middle angles
            middle_idx = num_angles // 2
            median_angle = np.degrees(self.average_angle(sorted_angles[middle_idx - 1], sorted_angles[middle_idx]))

        return median_angle

    def measure_angle(self) -> float | None:
        # Read a frame from the camera
        _, frame = self.cap.read()

        # Detect ArUco markers in the frame
        detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        corners, ids, __ = detector.detectMarkers(frame)

        angles = []
        angel_dif = 360 / self.number_of_tracker
        
        # If a marker was detected, calculate its rotation
        if ids is not None:
            for index, i in enumerate(corners):
                try:
                    ids_tmp = ids[index][0]
                except:
                    ids_tmp = ids

                angle = angel_dif * (ids_tmp)
                angle %= 360
                angles.append(angle)
            caluclated_angle = self.calculate_median_angle(angles)
        else:
            return None
        
        # Display the frame
        if self.debug:
            # Draw the detected markers on the frame
            frame_markers = cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            cv2.imshow('ArUco Tracker', frame_markers)

        self._last_angle = Angle(caluclated_angle)
        self._last_angle_recording = time()
        return self.last_angle

    def release(self) -> None:
        self.cap.release()
        if self.debug:
            cv2.destroyAllWindows()

class TestRotationSensor(RotationSensor):
    def __init__(self, start_angle = Angle(180.0), speed: float = 1.0, update_interval: int = 20, stage_diameter: float = 4.5) -> None:
        super().__init__()
        self.speed = speed
        self.stage_diameter = stage_diameter
        self.angular_velocity = 0.0  
        self.current_angle = start_angle
        self.update_interval = update_interval / 1000
        self.last_update = time()
        self.turn_forward = True

    @property
    def last_angle(self) -> Angle | None:
        return self.current_angle
    
    @property
    def last_angle_recording(self) -> float | None:
        return self.last_update

    def update(self, forward: bool, frequency: float) -> None:
        self.angular_velocity = (self.speed * (frequency / 60.0)) / (self.stage_diameter / 2) # speed: m/s, diameter: m, velocity: 1/s
        self.turn_forward = forward

    def measure_angle(self) -> float | None:
        dt = time() - self.last_update
        if dt > self.update_interval:
            dr = math.degrees(self.angular_velocity * dt) # v * s = rad
            if self.turn_forward:
                self.current_angle += Angle(dr)
            else:
                self.current_angle -= Angle(dr)
            self.last_update = time()
            return self.current_angle
        else:
            return None