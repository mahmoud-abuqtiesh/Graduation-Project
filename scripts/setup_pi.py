#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.capture._ssh import SshConnectError, scp_put, ssh_run
from src.capture.pi_config import CONFIG_PATH, load_pi_config, template_json

def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)

def _print_config_template() -> None:
    print(f"Pi config missing at {CONFIG_PATH}.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Create the file with this template:", file=sys.stderr)
    print("", file=sys.stderr)
    print(template_json(), file=sys.stderr)

def _ssh_check(cfg, command: str, label: str, *, timeout: float = 30.0) -> str:
    try:
        out, err, rc = ssh_run(cfg, command, timeout=timeout)
    except SshConnectError as exc:
        _die(f"[{label}] SSH failed: {exc}")
    if rc != 0:
        tail = (err.strip() or out.strip())[:400]
        _die(f"[{label}] remote exited {rc}. Output:\n{tail}")
    return out

def main() -> int:
    if not CONFIG_PATH.exists():
        _print_config_template()
        return 1

    cfg = load_pi_config(refresh=True)
    if not cfg.is_usable:
        _die(
            "pi.json is missing required fields. Need host, user, password, "
            "and install_dir."
        )

    print(f"[1/5] SSH connectivity to {cfg.user}@{cfg.host}...")
    _ssh_check(cfg, "echo connected", "ssh-test", timeout=10.0)

    print(f"[2/5] Preparing install dir at {cfg.install_dir} on the Pi...")
    _ssh_check(
        cfg,
        f"mkdir -p '{cfg.install_dir}/src/capture'",
        "mkdir-remote",
    )

    print("[3/5] Uploading src/capture/ to the Pi (SFTP)...")
    capture_dir = REPO_ROOT / "src" / "capture"
    if not capture_dir.is_dir():
        _die(f"Local src/capture/ not found at {capture_dir}")
    files = sorted(p for p in capture_dir.glob("*.py"))
    if not files:
        _die("No .py files under src/capture/ -- nothing to copy.")
    for src_path in files:
        remote_path = f"{cfg.install_dir}/src/capture/{src_path.name}"
        try:
            scp_put(cfg, str(src_path), remote_path)
        except SshConnectError as exc:
            _die(f"[scp:{src_path.name}] failed: {exc}")
        print(f"    uploaded {src_path.name}")

    print("    (touching src/__init__.py on the Pi)")
    _ssh_check(
        cfg,
        f"touch '{cfg.install_dir}/src/__init__.py'",
        "touch-init",
    )

    print("[4/5] Creating venv (if missing) and installing opencv-python + numpy...")
    venv_cmd = (
        f"set -e; cd '{cfg.install_dir}'; "
        f"if [ ! -d venv ]; then python3 -m venv venv; fi; "
        f"venv/bin/pip install --upgrade pip >/dev/null 2>&1 || true; "
        f"venv/bin/pip install --quiet opencv-python numpy"
    )
    _ssh_check(cfg, venv_cmd, "venv-install", timeout=300.0)

    print("[5/5] Running probe.py to verify cameras...")
    probe_cmd = (
        f"{cfg.install_dir}/venv/bin/python "
        f"{cfg.install_dir}/src/capture/probe.py"
    )
    try:
        out, err, rc = ssh_run(cfg, probe_cmd, timeout=30.0)
    except SshConnectError as exc:
        _die(f"[probe] SSH failed: {exc}")
    print(out.strip() or "(no cameras detected)")
    if rc != 0:
        print(err.strip(), file=sys.stderr)
        return rc

    print("")
    print("Pi setup complete.")
    if os.name == "posix":
        print("If the laptop has UFW enabled, you may need:")
        print(f"  sudo ufw allow in proto udp from {cfg.host}")
    else:
        print("If Windows Defender Firewall blocks inbound UDP, allow Python:")
        print("  Settings -> Privacy & security -> Windows Security -> Firewall")
    return 0

if __name__ == "__main__":
    sys.exit(main())
