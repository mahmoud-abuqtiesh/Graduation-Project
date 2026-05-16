from __future__ import annotations

import math
import random

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec4,
)

_SIDES = 6

_RINGS = (
    (160.0, 48, (12.0, 20.0), (28.0, 50.0),
     Vec4(0.32, 0.24, 0.18, 1.0), Vec4(0.78, 0.72, 0.60, 1.0)),
    (130.0, 36, (8.0, 14.0), (18.0, 32.0),
     Vec4(0.40, 0.30, 0.22, 1.0), Vec4(0.85, 0.78, 0.65, 1.0)),
    (100.0, 28, (5.0, 9.0), (8.0, 16.0),
     Vec4(0.45, 0.34, 0.24, 1.0), Vec4(0.88, 0.80, 0.66, 1.0)),
)

def _add_peak(
    vwriter: GeomVertexWriter,
    cwriter: GeomVertexWriter,
    tris: GeomTriangles,
    vert_idx_start: int,
    cx: float,
    cy: float,
    base_r: float,
    peak_h: float,
    base_color: Vec4,
    apex_color: Vec4,
) -> int:
    base_first = vert_idx_start
    for i in range(_SIDES):
        ang = 2.0 * math.pi * (i / _SIDES)
        bx = cx + base_r * math.cos(ang)
        by = cy + base_r * math.sin(ang)
        vwriter.addData3(bx, by, 0.0)
        cwriter.addData4(base_color)
    apex_idx = base_first + _SIDES
    vwriter.addData3(cx, cy, peak_h)
    cwriter.addData4(apex_color)

    for i in range(_SIDES):
        i_next = (i + 1) % _SIDES
        tris.addVertices(apex_idx, base_first + i_next, base_first + i)
        tris.closePrimitive()
    return _SIDES + 1

def build_mountains(parent: NodePath, seed: int = 7) -> NodePath:
    rng = random.Random(seed)

    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("mountains", fmt, Geom.UHStatic)
    total_peaks = sum(spec[1] for spec in _RINGS)
    vdata.setNumRows(total_peaks * (_SIDES + 1))

    vwriter = GeomVertexWriter(vdata, "vertex")
    cwriter = GeomVertexWriter(vdata, "color")
    tris = GeomTriangles(Geom.UHStatic)

    vert_idx = 0
    for radius, count, base_r_range, height_range, base_color, apex_color in _RINGS:
        angular_jitter = 0.45 / count
        for i in range(count):
            a = 2.0 * math.pi * (i / count + rng.uniform(-angular_jitter, angular_jitter))
            r_jit = radius * rng.uniform(0.92, 1.08)
            cx = r_jit * math.cos(a)
            cy = r_jit * math.sin(a)
            base_r = rng.uniform(*base_r_range)
            peak_h = rng.uniform(*height_range)
            added = _add_peak(
                vwriter, cwriter, tris, vert_idx,
                cx, cy, base_r, peak_h, base_color, apex_color,
            )
            vert_idx += added

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("mountains")
    node.addGeom(geom)

    np_ = parent.attachNewNode(node)
    np_.setLightOff()
    return np_
