
from __future__ import annotations

import platform
from pathlib import Path
from typing import Optional

__all__ = [
    "stable_id_for_index",
    "build_stable_id",
    "build_pi_stable_id",
    "extract_index_from_stable_id",
    "INDEX_PREFIX",
    "USB_PREFIX",
    "PI_PREFIX",
]

INDEX_PREFIX = "index:"
USB_PREFIX = "usb:"
PI_PREFIX = "pi:"

_BAD_SERIAL_TOKENS = {
    "",
    "0",
    "0000",
    "00000000",
    "n/a",
    "na",
    "none",
    "null",
    "default",
    "unknown",
    "(none)",
    "01.00.00",
    "00.00.00",
    "0.0.0",
    "1.0.0",
}

def _read_sysfs(path: Path) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except (OSError, ValueError):
        return None

def _looks_like_useful_serial(
    serial: Optional[str],
    vendor: Optional[str],
    product: Optional[str],
    model: Optional[str],
) -> bool:
    if not serial:
        return False
    s = serial.strip().lower()
    if s in _BAD_SERIAL_TOKENS:
        return False
    if vendor and product and s == f"{vendor.lower()}:{product.lower()}":
        return False
    if model and s == model.strip().lower():
        return False
    if product and s == product.strip().lower():
        return False
    if all(c == "0" for c in s):
        return False
    return True

def _usb_port_for_video(video_node: str) -> Optional[str]:
    sys_dev = Path(f"/sys/class/video4linux/{video_node}/device")
    if not sys_dev.exists():
        return None
    try:
        iface = sys_dev.resolve()
        usb_dev_dir = iface.parent
        return usb_dev_dir.name or None
    except OSError:
        return None

def build_stable_id(
    vendor_id: Optional[str],
    product_id: Optional[str],
    serial: Optional[str],
    usb_port: Optional[str],
    product_name: Optional[str] = None,
) -> Optional[str]:
    vendor = (vendor_id or "").strip().lower()
    product = (product_id or "").strip().lower()
    if not vendor or not product:
        return None

    if _looks_like_useful_serial(serial, vendor, product, product_name):
        return f"{USB_PREFIX}{vendor}:{product}:serial:{serial.strip()}"

    if usb_port:
        return f"{USB_PREFIX}{vendor}:{product}:port:{usb_port.strip()}"

    return None

def build_pi_stable_id(probe_dict: dict) -> Optional[str]:
    base = build_stable_id(
        vendor_id=probe_dict.get("vendor"),
        product_id=probe_dict.get("product"),
        serial=probe_dict.get("serial"),
        usb_port=probe_dict.get("usb_port"),
        product_name=probe_dict.get("product_name"),
    )
    if base is None:
        return None
    return f"{PI_PREFIX}{base}"

def stable_id_for_index(index: int) -> Optional[str]:
    if platform.system() != "Linux":
        return None
    video_node = f"video{int(index)}"
    sys_dev = Path(f"/sys/class/video4linux/{video_node}/device")
    if not sys_dev.exists():
        return None

    try:
        usb_dev_dir = sys_dev.resolve().parent
    except OSError:
        return None

    vendor = _read_sysfs(usb_dev_dir / "idVendor")
    product = _read_sysfs(usb_dev_dir / "idProduct")
    serial = _read_sysfs(usb_dev_dir / "serial")
    product_name = _read_sysfs(usb_dev_dir / "product")
    usb_port = _usb_port_for_video(video_node)

    return build_stable_id(
        vendor_id=vendor,
        product_id=product,
        serial=serial,
        usb_port=usb_port,
        product_name=product_name,
    )

def extract_index_from_stable_id(stable_id: Optional[str]) -> Optional[int]:
    if not stable_id:
        return None
    if stable_id.startswith(INDEX_PREFIX):
        try:
            return int(stable_id[len(INDEX_PREFIX):])
        except ValueError:
            return None
    return None
