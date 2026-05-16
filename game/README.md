# Horsin' Around

A Panda3D demo we built to show off the EyeCursor head/eye-gaze control stack. You ride an automated rollercoaster around a track and photograph procedurally placed horses. While the photo countdown is running, leaning toward the screen telephoto-zooms the lens via stereo depth piped over a UDP socket. QUAKE-style pixel look throughout.

## Stack

| Concern   | Choice                                |
|-----------|---------------------------------------|
| Engine    | Panda3D >= 1.10.14                    |
| Language  | Python 3.12                           |
| Aesthetic | QUAKE / pixel art (nearest-neighbor)  |
| IPC       | UDP `127.0.0.1:7345`, JSON depth      |

## Quick start

The game runs from the parent EyeCursor project's `venv`. From the repo root:

```bash
./venv/bin/pip install -r requirements.txt
./launchers/launch_game.sh
```

The launcher just `cd`s back to the repo root and runs `python -m game.app.main`, so if you'd rather invoke it directly that works too.

## Controls

| Input                                               | Action                                                       |
|-----------------------------------------------------|--------------------------------------------------------------|
| Mouse / OS cursor                                   | Look around (cart-relative; centered = look down the track)  |
| Photo trigger (left click / spacebar / right click) | Hold to compose and shoot                                    |
| Up / Down arrows                                    | Navigate menus                                               |
| Left / Right arrows (in Settings)                   | Cycle the focused option                                     |
| Enter / Return                                      | Activate focused option                                      |
| ESC                                                 | Pause overlay while riding, back out elsewhere               |

The photo trigger is whatever you set in Settings. Default is left click.

The main menu has five entries: MAPS (track picker), DEX (species you've photographed so far), GALLERY (your saved shots), SETTINGS, and QUIT.

## Settings

Persisted to `game/config.json` and written on every change. Valid values come straight from `game/core/settings.py`.

| Key                  | Valid values                                  | Notes                                                     |
|----------------------|-----------------------------------------------|-----------------------------------------------------------|
| `photo_trigger`      | `left_click`, `spacebar`, `right_click`       | Which input arms the photo countdown.                     |
| `countdown_duration` | `0.5`, `1.0`, `1.5`, `2.0` (seconds)          | How long to hold the trigger before the shutter fires.    |
| `cart_speed`         | `slow`, `normal`, `fast`                      | Maps to `1.5` / `3.0` / `6.0` units per second.           |
| `sfx_volume`         | `0.0`, `0.25`, `0.5`, `0.75`, `1.0`           | Click, shutter, countdown tick, chime, etc.               |
| `music_volume`       | `0.0`, `0.25`, `0.5`, `0.75`, `1.0`           | Ambient loop.                                             |

Anything outside the valid set silently falls back to the default.

## How the depth zoom works

When EyeCursor's "Two-Camera Head Pose" mode is running, the `DepthBroadcaster` in `src/core/modes/two_camera_head_pose.py` opens a UDP socket and sends `{"depth": <float>}` to `127.0.0.1:7345` rate-limited to 30 Hz.

On the game side, `game/core/depth_client.py` binds the same port on a daemon thread and stashes the most recent value. Anything older than 2 seconds is treated as missing, so if the stereo mode is paused or never started, the game just plays with no zoom (FOV stays at 90 deg).

While the trigger is held, `PhotoManager` captures a baseline depth on press and then maps `abs(baseline) - abs(current)` to FOV. Roughly 20 cm closer = full zoom (FOV 30 deg). Pulling further away from the baseline is clamped, so backing off doesn't widen the lens. We use `abs()` on both values so it doesn't matter which sign convention the stereo pipeline emits. Baseline resets after every shot.

## Project layout

```
game/
├── app/        # ShowBase entry point and the SceneManager (main.py)
├── core/       # Depth client, settings, photo manager, track/cart/rail/horse builders, asset gen
├── scenes/     # Menus, settings, gameplay, gallery, dex, map select, pause overlay
├── assets/     # textures/, fonts/, audio/ - all populated on first run
└── photos/     # Saved PNGs plus JSON sidecars
```

Notable files if you're poking around:

- `game/app/main.py` - boots Panda3D, owns the depth client, registers every scene.
- `game/core/photo_manager.py` - countdown state machine, FOV math, flash, slide-in preview, screenshot save.
- `game/core/settings.py` - the single source of truth for valid setting values.
- `game/core/depth_client.py` - UDP receiver, 2-second freshness window.
- `game/core/asset_gen.py` - procedurally generates textures and the wave SFX, downloads the font.
- `game/scenes/game_scene.py` - the actual ride loop.
- `game/scenes/gallery_scene.py` - thumbnails of saved photos.
- `game/scenes/dex_scene.py` - species checklist driven by the JSON sidecars.

## Assets

- **Horse models** are built from stacked Panda3D primitives. No `.egg` files ship with the repo.
- **Ground, sky, sand, desert sky textures** are 64x64 PNGs generated by `game/core/asset_gen.py` on first launch, loaded with nearest-neighbor filtering for the chunky pixel look.
- **Audio** lives in `game/assets/audio/` and is loaded if present (`ui_click.ogg`, `ambient.ogg`, `shutter.ogg`, `countdown_tick.ogg`, `photo_saved.ogg`, `wave_emote.wav`). The wave sound effect is synthesised on first launch if it's missing; the others are expected to already be in the repo.
- **Pixel font** is Press Start 2P (OFL-1.1), fetched from the Google Fonts repo on first launch and written to `game/assets/fonts/pixel.ttf`. If the download fails (no network, timeout, etc.) the game just uses Panda3D's default font.

## Photo preview

After every successful capture the just-saved PNG slides up from the bottom-right, holds for about 2.5 seconds, then slides back out. Bordered in the QUAKE accent green so it stays readable against the world. Timings live at the top of `game/core/photo_manager.py` if you want to tweak them.

## Photo output

Screenshots go to `game/photos/YYYY-MM-DD_HH-MM-SS.png`. Alongside each PNG, `PhotoManager` writes a `.json` sidecar containing the `map_id` of the track you were on and the `species_ids` of any horses visible in the frame. The Dex scene reads those sidecars to figure out what you've discovered.

The directory is git-ignored.

## License

Game code is part of the EyeCursor graduation project and inherits the parent repo's license. Press Start 2P is OFL-1.1 from Google Fonts.
