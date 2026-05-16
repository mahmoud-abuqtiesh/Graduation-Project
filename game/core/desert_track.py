from __future__ import annotations

import math
from typing import Tuple

from panda3d.core import Vec3

class DesertTrack:
    def __init__(self, straight: float = 40.0, radius: float = 15.0, height: float = 1.5) -> None:
        self.straight = straight
        self.radius = radius
        self.height = height
        self.circumference = 2.0 * straight + 2.0 * math.pi * radius

        self._s1_end = straight
        self._s2_end = straight + math.pi * radius
        self._s3_end = 2.0 * straight + math.pi * radius
        self._s4_end = self.circumference

    def evaluate(self, t: float) -> Tuple[Vec3, Vec3]:
        s = (t % 1.0) * self.circumference
        L = self.straight
        r = self.radius
        h = self.height

        if s < self._s1_end:
            u = s
            x = L / 2.0 - u
            y = r
            tangent = Vec3(-1.0, 0.0, 0.0)
            return Vec3(x, y, h), tangent

        if s < self._s2_end:
            u = s - self._s1_end
            theta = u / r
            angle = math.pi / 2.0 + theta
            cx, cy = -L / 2.0, 0.0
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            tangent = Vec3(-math.sin(angle), math.cos(angle), 0.0)
            return Vec3(x, y, h), tangent

        if s < self._s3_end:
            u = s - self._s2_end
            x = -L / 2.0 + u
            y = -r
            tangent = Vec3(1.0, 0.0, 0.0)
            return Vec3(x, y, h), tangent

        u = s - self._s3_end
        theta = u / r
        angle = -math.pi / 2.0 + theta
        cx, cy = L / 2.0, 0.0
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        tangent = Vec3(-math.sin(angle), math.cos(angle), 0.0)
        return Vec3(x, y, h), tangent

    def advance(self, t: float, speed: float, dt: float) -> float:
        if self.circumference <= 0:
            return 0.0
        t += (speed * dt) / self.circumference
        return t % 1.0
