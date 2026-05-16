from __future__ import annotations

import urllib.request
import wave
from pathlib import Path

import cv2
import numpy as np

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEXTURES_DIR = ASSETS_DIR / "textures"
FONTS_DIR = ASSETS_DIR / "fonts"
AUDIO_DIR = ASSETS_DIR / "audio"

GRASS_PATH = TEXTURES_DIR / "grass.png"
SKY_PATH = TEXTURES_DIR / "sky.png"
SAND_PATH = TEXTURES_DIR / "sand.png"
DESERT_SKY_PATH = TEXTURES_DIR / "desert_sky.png"
WAVE_SFX_PATH = AUDIO_DIR / "wave_emote.wav"
FONT_PATH = FONTS_DIR / "pixel.ttf"

FONT_URL = "https://github.com/google/fonts/raw/main/ofl/pressstart2p/PressStart2P-Regular.ttf"

def _make_grass(path: Path) -> None:
    rng = np.random.default_rng(42)
    base = np.zeros((64, 64, 3), dtype=np.uint8)
    base[..., 1] = 110
    base[..., 0] = 30
    base[..., 2] = 40
    jitter = rng.integers(-25, 25, size=(64, 64, 3), dtype=np.int16)
    out = np.clip(base.astype(np.int16) + jitter, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), out)

def _make_sky(path: Path) -> None:
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    for y in range(64):
        t = y / 63.0
        r = int(80 + (180 - 80) * t)
        g = int(140 + (220 - 140) * t)
        b = int(200 + (240 - 200) * t)
        img[y, :, 0] = b
        img[y, :, 1] = g
        img[y, :, 2] = r
    cv2.imwrite(str(path), img)

def _make_sand(path: Path) -> None:
    rng = np.random.default_rng(99)
    base = np.zeros((64, 64, 3), dtype=np.uint8)
    base[..., 0] = 110
    base[..., 1] = 165
    base[..., 2] = 195
    jitter = rng.integers(-20, 20, size=(64, 64, 3), dtype=np.int16)
    out = np.clip(base.astype(np.int16) + jitter, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), out)

def _make_desert_sky(path: Path) -> None:
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    top_rgb = (245, 175, 95)
    bot_rgb = (225, 205, 175)
    for y in range(64):
        t = y / 63.0
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * t)
        img[y, :, 0] = b
        img[y, :, 1] = g
        img[y, :, 2] = r
    cv2.imwrite(str(path), img)

def _make_wave_sfx(path: Path) -> None:
    sample_rate = 22050
    tone_dur = 0.15
    gap_dur = 0.05
    n_tone = int(sample_rate * tone_dur)
    n_gap = int(sample_rate * gap_dur)

    def _envelope(n: int) -> np.ndarray:
        t = np.arange(n, dtype=np.float32) / max(1, n - 1)
        attack = np.clip(t / 0.05, 0.0, 1.0)
        decay = np.clip(1.0 - (t - 0.05) / 0.95, 0.0, 1.0)
        return attack * decay

    def _tone(freq: float) -> np.ndarray:
        t = np.arange(n_tone, dtype=np.float32) / sample_rate
        wave_arr = np.sin(2.0 * np.pi * freq * t)
        return wave_arr * _envelope(n_tone) * 0.5

    silence = np.zeros(n_gap, dtype=np.float32)
    samples = np.concatenate([_tone(600.0), silence, _tone(900.0)])
    pcm = np.clip(samples * 32767.0, -32768.0, 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())

def _try_download_font(path: Path) -> None:
    try:
        with urllib.request.urlopen(FONT_URL, timeout=5) as resp:
            data = resp.read()
        if data and len(data) > 1024:
            path.write_bytes(data)
    except Exception:
        pass

def ensure_assets() -> None:
    TEXTURES_DIR.mkdir(parents=True, exist_ok=True)
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if not GRASS_PATH.exists():
        try:
            _make_grass(GRASS_PATH)
        except Exception:
            pass
    if not SKY_PATH.exists():
        try:
            _make_sky(SKY_PATH)
        except Exception:
            pass
    if not SAND_PATH.exists():
        try:
            _make_sand(SAND_PATH)
        except Exception:
            pass
    if not DESERT_SKY_PATH.exists():
        try:
            _make_desert_sky(DESERT_SKY_PATH)
        except Exception:
            pass
    if not WAVE_SFX_PATH.exists():
        try:
            _make_wave_sfx(WAVE_SFX_PATH)
        except Exception:
            pass
    if not FONT_PATH.exists():
        _try_download_font(FONT_PATH)

def font_path() -> Path | None:
    return FONT_PATH if FONT_PATH.exists() else None

def grass_path() -> Path | None:
    return GRASS_PATH if GRASS_PATH.exists() else None

def sky_path() -> Path | None:
    return SKY_PATH if SKY_PATH.exists() else None

def sand_path() -> Path | None:
    return SAND_PATH if SAND_PATH.exists() else None

def desert_sky_path() -> Path | None:
    return DESERT_SKY_PATH if DESERT_SKY_PATH.exists() else None

def audio_path(name: str) -> Path | None:
    p = AUDIO_DIR / name
    return p if p.exists() else None
