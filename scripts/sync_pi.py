#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.capture._ssh import SshConnectError, scp_put, ssh_run
from src.capture.pi_config import CONFIG_PATH, load_pi_config

def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)

def main() -> int:
    if not CONFIG_PATH.exists():
        _die(
            f"Pi config missing at {CONFIG_PATH}. "
            f"Run scripts/setup_pi.py first."
        )

    cfg = load_pi_config(refresh=True)
    if not cfg.is_usable:
        _die("pi.json incomplete -- need host/user/password/install_dir.")

    capture_dir = REPO_ROOT / "src" / "capture"
    files = sorted(p for p in capture_dir.glob("*.py"))
    if not files:
        _die("No .py files under src/capture/.")

    try:
        ssh_run(cfg, f"mkdir -p '{cfg.install_dir}/src/capture'", timeout=10.0)
        for src_path in files:
            remote_path = f"{cfg.install_dir}/src/capture/{src_path.name}"
            scp_put(cfg, str(src_path), remote_path)
    except SshConnectError as exc:
        _die(str(exc))

    print(f"Synced {len(files)} file(s) to {cfg.user}@{cfg.host}:{cfg.install_dir}/")
    return 0

if __name__ == "__main__":
    sys.exit(main())
