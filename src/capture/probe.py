
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

def _read(path: Path) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except (OSError, ValueError):
        return None

def _video_indices() -> List[int]:
    indices: List[int] = []
    for entry in sorted(Path("/dev").glob("video*")):
        name = entry.name
        if not name.startswith("video"):
            continue
        try:
            indices.append(int(name[len("video"):]))
        except ValueError:
            continue
    return indices

def _sysfs_for(index: int) -> Dict[str, str]:
    sys_dev = Path(f"/sys/class/video4linux/video{index}/device")
    info: Dict[str, str] = {}
    if not sys_dev.exists():
        return info
    try:
        usb_dev_dir = sys_dev.resolve().parent
    except OSError:
        return info
    for field, key in (
        ("idVendor", "vendor"),
        ("idProduct", "product"),
        ("serial", "serial"),
        ("product", "product_name"),
    ):
        value = _read(usb_dev_dir / field)
        if value is not None:
            info[key] = value
    info["usb_port"] = usb_dev_dir.name
    return info

def _try_open(index: int):
    try:
        import cv2
    except ImportError as exc:
        print(f"ERROR: cv2 not available in venv: {exc}", file=sys.stderr)
        sys.exit(2)

    cap = cv2.VideoCapture(index)
    try:
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        height, width = frame.shape[:2]
        return int(width), int(height)
    finally:
        cap.release()

def main() -> int:
    seen_keys = set()
    cameras: List[Dict[str, object]] = []
    for index in _video_indices():
        sysfs = _sysfs_for(index)
        if not sysfs:
            continue
        vendor = sysfs.get("vendor", "")
        product = sysfs.get("product", "")
        usb_port = sysfs.get("usb_port", "")
        if not vendor or not product:
            continue
        key = (vendor, product, usb_port)
        if key in seen_keys:
            continue
        wh = _try_open(index)
        if wh is None:
            continue
        seen_keys.add(key)
        width, height = wh
        cameras.append(
            {
                "index": index,
                "vendor": vendor,
                "product": product,
                "serial": sysfs.get("serial", ""),
                "product_name": sysfs.get("product_name", ""),
                "usb_port": usb_port,
                "width": width,
                "height": height,
            }
        )
    json.dump(cameras, sys.stdout)
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
