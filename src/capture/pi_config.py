
from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

def _default_config_path() -> Path:
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "EyeCursor" / "pi.json"
    return Path(os.path.expanduser("~/.config/EyeCursor/pi.json"))

CONFIG_PATH = _default_config_path()

DEFAULT_HOST = "192.168.50.2"
DEFAULT_USER = "pi4"
DEFAULT_INSTALL_DIR = "/home/pi4/eyecursor-capture"
DEFAULT_LAPTOP_HOST = "192.168.50.1"

@dataclass(frozen=True)
class PiConfig:
    host: str
    user: str
    password: str
    install_dir: str
    laptop_host: str

    @property
    def is_usable(self) -> bool:
        return bool(self.host and self.user and self.password and self.install_dir)

_cached: Optional[PiConfig] = None

def load_pi_config(refresh: bool = False) -> PiConfig:
    global _cached
    if _cached is not None and not refresh:
        return _cached

    data = {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}

    _cached = PiConfig(
        host=str(data.get("host") or DEFAULT_HOST),
        user=str(data.get("user") or DEFAULT_USER),
        password=str(data.get("password") or ""),
        install_dir=str(data.get("install_dir") or DEFAULT_INSTALL_DIR),
        laptop_host=str(data.get("laptop_host") or DEFAULT_LAPTOP_HOST),
    )
    return _cached

def template_json() -> str:
    return json.dumps(
        {
            "host": DEFAULT_HOST,
            "user": DEFAULT_USER,
            "password": "<your pi password>",
            "install_dir": DEFAULT_INSTALL_DIR,
            "laptop_host": DEFAULT_LAPTOP_HOST,
        },
        indent=2,
    )
