from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CameraInfo:
    index: int
    width: int = 0
    height: int = 0
    label: str = ""
    is_available: bool = True
    stable_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.label:
            self.label = f"Camera {self.index}"
