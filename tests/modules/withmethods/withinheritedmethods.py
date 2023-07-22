from .withmethods import Point
from tests.modules import withmethods


class ThreeDimensionalPoint(Point):

    def __init__(self, x: int, y: str, z: float):
        super().__init__(x=x, y=y)
        self.z = z

    def move(self, offset: int):
        self.x += offset

    def check_positive(self) -> bool:
        return self.x > 0


class ThreeDimensionalCoordinates(withmethods.withmethods.Coordinates):

    def __init__(self, x: float, y: float, z: float):
        super().__init__(x=x, y=y)
        self.z = z

    def move(self, offset: int):
        self.x += offset

    def check_negative(self) -> bool:
        return self.x < 0
