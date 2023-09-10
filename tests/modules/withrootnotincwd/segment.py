from dataclasses import dataclass

from tests.modules.withrootnotincwd.point import Point


@dataclass
class Segment:
    a: Point
    b: Point
