from typing import Dict, Iterable, Optional, Tuple

BLENDSHAPE_KEYS = (
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthPucker",
    "mouthRollUpper",
    "mouthRollLower",
    "mouthPressLeft",
    "mouthPressRight",
)

def extract_blendshapes(categories: Optional[Iterable]) -> Dict[str, float]:
    result = {key: 0.0 for key in BLENDSHAPE_KEYS}
    if categories is None:
        return result

    for category in categories:
        name = getattr(category, "category_name", None)
        if name in result:
            score = getattr(category, "score", 0.0)
            try:
                result[name] = float(score)
            except (TypeError, ValueError):
                result[name] = 0.0
    return result

def compute_smirk_activations(blendshapes: Dict[str, float]) -> Tuple[float, float]:
    left = float(blendshapes.get("mouthSmileLeft", 0.0))
    right = float(blendshapes.get("mouthSmileRight", 0.0))
    return left, right

def pucker_value(blendshapes: Dict[str, float]) -> float:
    return float(blendshapes.get("mouthPucker", 0.0))

def tuck_value(blendshapes: Dict[str, float]) -> float:
    return max(
        float(blendshapes.get("mouthRollUpper", 0.0)),
        float(blendshapes.get("mouthRollLower", 0.0)),
        float(blendshapes.get("mouthPressLeft", 0.0)),
        float(blendshapes.get("mouthPressRight", 0.0)),
    )
