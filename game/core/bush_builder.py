from __future__ import annotations

import math
import random

from panda3d.core import NodePath, Vec3, Vec4

_GREENS = (
    Vec4(0.40, 0.52, 0.28, 1.0),
    Vec4(0.34, 0.46, 0.22, 1.0),
    Vec4(0.50, 0.58, 0.30, 1.0),
    Vec4(0.42, 0.50, 0.20, 1.0),
)

def _add_clump(loader, parent: NodePath, scale: Vec3, pos: Vec3, color: Vec4) -> None:
    np_ = loader.loadModel("models/box")
    np_.reparentTo(parent)
    np_.setScale(scale)
    np_.setPos(pos.x - scale.x / 2.0, pos.y - scale.y / 2.0, pos.z)
    np_.setColor(color)

def _build_bush(loader, root: NodePath, rng: random.Random) -> None:
    base_color = rng.choice(_GREENS)
    n_clumps = rng.randint(2, 4)
    for _ in range(n_clumps):
        sx = rng.uniform(0.5, 1.4)
        sy = rng.uniform(0.5, 1.4)
        sz = rng.uniform(0.4, 0.95)
        ox = rng.uniform(-0.4, 0.4)
        oy = rng.uniform(-0.4, 0.4)
        var = rng.uniform(-0.05, 0.05)
        c = Vec4(
            max(0.0, min(1.0, base_color.x + var)),
            max(0.0, min(1.0, base_color.y + var)),
            max(0.0, min(1.0, base_color.z + var)),
            1.0,
        )
        _add_clump(loader, root, Vec3(sx, sy, sz), Vec3(ox, oy, 0.0), c)

def scatter_bushes(
    loader,
    parent: NodePath,
    count: int = 110,
    inner_r: float = 30.0,
    outer_r: float = 92.0,
    seed: int = 13,
) -> NodePath:
    rng = random.Random(seed)
    root = parent.attachNewNode("bushes")
    for _ in range(count):
        ang = rng.uniform(0.0, 2.0 * math.pi)
        r = rng.uniform(inner_r, outer_r)
        x = r * math.cos(ang)
        y = r * math.sin(ang)
        bush = root.attachNewNode("bush")
        bush.setPos(x, y, 0.0)
        bush.setH(rng.uniform(0.0, 360.0))
        _build_bush(loader, bush, rng)
    return root
