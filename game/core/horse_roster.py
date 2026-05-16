from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

from panda3d.core import Vec4

class Rarity(IntEnum):
    COMMON = 1
    RARE = 2
    LEGENDARY = 3

SPAWN_WEIGHTS = {
    Rarity.COMMON: 4,
    Rarity.RARE: 1,
    Rarity.LEGENDARY: 1,
}

@dataclass(frozen=True)
class HorseSpecies:
    id: str
    name: str
    map_id: str
    rarity: Rarity
    color: Vec4

ROSTER: List[HorseSpecies] = [
    HorseSpecies(
        id="meadow_chestnut", name="CHESTNUT", map_id="meadow",
        rarity=Rarity.COMMON, color=Vec4(0.55, 0.30, 0.15, 1.0),
    ),
    HorseSpecies(
        id="meadow_bay", name="BAY", map_id="meadow",
        rarity=Rarity.COMMON, color=Vec4(0.38, 0.22, 0.12, 1.0),
    ),
    HorseSpecies(
        id="meadow_inky", name="INKY", map_id="meadow",
        rarity=Rarity.COMMON, color=Vec4(0.08, 0.07, 0.07, 1.0),
    ),
    HorseSpecies(
        id="meadow_dapple", name="DAPPLE", map_id="meadow",
        rarity=Rarity.COMMON, color=Vec4(0.62, 0.62, 0.65, 1.0),
    ),
    HorseSpecies(
        id="meadow_snow", name="SNOW", map_id="meadow",
        rarity=Rarity.COMMON, color=Vec4(0.94, 0.92, 0.88, 1.0),
    ),
    HorseSpecies(
        id="meadow_sundancer", name="SUNDANCER", map_id="meadow",
        rarity=Rarity.RARE, color=Vec4(0.95, 0.78, 0.25, 1.0),
    ),
    HorseSpecies(
        id="highland_pony", name="HIGHLAND", map_id="highlands",
        rarity=Rarity.COMMON, color=Vec4(0.32, 0.20, 0.12, 1.0),
    ),
    HorseSpecies(
        id="highland_birch", name="BIRCH", map_id="highlands",
        rarity=Rarity.COMMON, color=Vec4(0.62, 0.42, 0.22, 1.0),
    ),
    HorseSpecies(
        id="highland_storm", name="STORM", map_id="highlands",
        rarity=Rarity.COMMON, color=Vec4(0.10, 0.10, 0.12, 1.0),
    ),
    HorseSpecies(
        id="highland_roan", name="ROAN", map_id="highlands",
        rarity=Rarity.COMMON, color=Vec4(0.50, 0.52, 0.55, 1.0),
    ),
    HorseSpecies(
        id="highland_drifter", name="DRIFTER", map_id="highlands",
        rarity=Rarity.COMMON, color=Vec4(0.92, 0.94, 0.96, 1.0),
    ),
    HorseSpecies(
        id="highland_aureate", name="AUREATE", map_id="highlands",
        rarity=Rarity.RARE, color=Vec4(0.92, 0.74, 0.20, 1.0),
    ),
    HorseSpecies(
        id="desert_mustang", name="MUSTANG", map_id="desert",
        rarity=Rarity.COMMON, color=Vec4(0.55, 0.30, 0.15, 1.0),
    ),
    HorseSpecies(
        id="desert_buckskin", name="BUCKSKIN", map_id="desert",
        rarity=Rarity.COMMON, color=Vec4(0.42, 0.28, 0.14, 1.0),
    ),
    HorseSpecies(
        id="desert_coal", name="COAL", map_id="desert",
        rarity=Rarity.COMMON, color=Vec4(0.10, 0.09, 0.08, 1.0),
    ),
    HorseSpecies(
        id="desert_dusty", name="DUSTY", map_id="desert",
        rarity=Rarity.COMMON, color=Vec4(0.78, 0.70, 0.58, 1.0),
    ),
    HorseSpecies(
        id="desert_ghost", name="GHOST", map_id="desert",
        rarity=Rarity.COMMON, color=Vec4(0.95, 0.92, 0.85, 1.0),
    ),
    HorseSpecies(
        id="desert_palomino", name="PALOMINO", map_id="desert",
        rarity=Rarity.RARE, color=Vec4(0.96, 0.80, 0.30, 1.0),
    ),
]

def roster_for_map(map_id: str) -> List[HorseSpecies]:
    return [s for s in ROSTER if s.map_id == map_id]

def species_by_id(species_id: str) -> Optional[HorseSpecies]:
    for s in ROSTER:
        if s.id == species_id:
            return s
    return None

def pick_species(rng: random.Random, map_id: str) -> HorseSpecies:
    pool = roster_for_map(map_id)
    if not pool:
        raise ValueError(f"no species for map_id={map_id!r}")
    weights = [SPAWN_WEIGHTS[s.rarity] for s in pool]
    return rng.choices(pool, weights=weights, k=1)[0]
