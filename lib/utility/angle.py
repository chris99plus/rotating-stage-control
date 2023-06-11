from typing import Any
import math

class Angle:
    def __init__(self, angle: Any) -> None:
        self.angle = angle.angle \
            if isinstance(angle, Angle) \
            else float(angle % 360)

    @staticmethod
    def to_angle(angle: Any) -> 'Angle':
        if isinstance(angle, Angle):
            return angle
        else:
            return Angle(angle)

    def __float__(self) -> float:
        return self.angle
    
    def __int__(self) -> int:
        return round(self.angle)
    
    def __str__(self) -> str:
        return str(self.angle)
    
    def __lt__(self, other: Any) -> bool:
        o = self.to_angle(other)
        return self.angle < o.angle

    def __le__(self, other: Any) -> bool:
        o = self.to_angle(other)
        return self.angle <= o.angle

    def __eq__(self, other: Any) -> bool:
        o = self.to_angle(other)
        return self.angle == o.angle

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __gt__(self, other: Any) -> bool:
        return not (self <= other)

    def __ge__(self, other: Any) -> bool:
        return not (self < other)

    def __add__(self, other: Any) -> 'Angle':
        o = self.to_angle(other)
        return Angle((self.angle + o.angle) % 360)

    def __sub__(self, other: Any) -> 'Angle':
        o = self.to_angle(other)
        if self.angle < self.angle:
            return Angle((360 - (o.angle - self.angle)) % 360)
        else:
            return Angle(self.angle - o.angle)

    def radian(self) -> float:
        return math.radians(self.angle)
    
    def round(self, ndigits: int = None) -> 'Angle':
        return Angle(round(self.angle, ndigits))

    def delta(self, other: Any) -> float:
        o = self.to_angle(other)

        # Calculate the absolute difference between the angles
        diff = abs(self.angle - o.angle)

        # Adjust the difference to be between 0 and 180 degrees
        if diff > 180:
            diff = 360 - diff

        return diff
        
def angle_avg(angle_list: list[Angle]) -> Angle:
    x_sum = 0.0
    y_sum = 0.0

    for angle in angle_list:
        x_sum += math.cos(math.radians(angle.angle))
        y_sum += math.sin(math.radians(angle.angle))

    avg_x = x_sum / len(angle_list)
    avg_y = y_sum / len(angle_list)

    durchschnitt_winkel = math.degrees(math.atan2(avg_y, avg_x))
    if durchschnitt_winkel < 0:
        durchschnitt_winkel += 360.0

    return Angle(durchschnitt_winkel)