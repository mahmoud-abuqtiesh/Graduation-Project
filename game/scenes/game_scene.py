from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional

from direct.gui.DirectGui import DirectLabel
from panda3d.core import (
    AmbientLight,
    CardMaker,
    DirectionalLight,
    Filename,
    LineSegs,
    NodePath,
    SamplerState,
    TextNode,
    TextureStage,
    Vec3,
    Vec4,
)

from game.core import asset_gen, settings
from game.core.bush_builder import scatter_bushes
from game.core.camera_controller import CameraController
from game.core.cart_builder import build_cart
from game.core.horse_spawner import spawn_horses
from game.core.maps import DEFAULT_MAP_ID, get_map
from game.core.mountain_builder import build_mountains
from game.core.photo_manager import PhotoManager, PhotoState
from game.core.rail_builder import build_rails
from game.scenes.base_scene import BaseScene

GROUND_SIZE = 200.0
DESERT_GROUND_SIZE = 400.0
RETICLE_HALF = 0.018
RETICLE_GAP = 0.006
FILL_RING_RADIUS = 0.045
FILL_RING_SEGMENTS = 48

WAVE_FADE_IN = 0.18
WAVE_HOLD = 0.55
WAVE_FADE_OUT = 0.40
WAVE_COOLDOWN = WAVE_FADE_IN + WAVE_HOLD + WAVE_FADE_OUT + 0.05
WAVE_SCALE_START = 0.06
WAVE_SCALE_END = 0.09
WAVE_TEXT_RGB = (1.0, 0.92, 0.45)

class GameScene(BaseScene):
    name = "game"
    cursor_visible = False

    def __init__(self, app) -> None:
        super().__init__(app)
        self.world: NodePath | None = None
        self.cart: NodePath | None = None
        self.camera_pivot: NodePath | None = None
        self.hud_root: NodePath | None = None
        self.fill_ring_node: NodePath | None = None
        self.track = None
        self.t_param: float = 0.0
        self.speed: float = 3.0
        self.cam_ctrl: CameraController | None = None
        self.photo: PhotoManager | None = None
        self._lights: list = []
        self._accept_keys: list = []
        self._has_camera_state = False
        self._saved_cam_parent = None
        self.map_id: str = DEFAULT_MAP_ID
        self.spawned_horses: List[NodePath] = []
        self._cart_sfx = None
        self._mountains: NodePath | None = None
        self._wave_label: DirectLabel | None = None
        self._wave_state: str = "idle"
        self._wave_elapsed: float = 0.0
        self._wave_cooldown: float = 0.0
        self._wave_sfx = None

    def enter(self, **kwargs) -> None:
        self.frozen = False
        base = self.app.base

        self.map_id = kwargs.get("map_id", DEFAULT_MAP_ID)
        map_def = get_map(self.map_id)

        self.world = NodePath("game_world")
        self.world.reparentTo(base.render)

        self._build_environment()

        self.track = map_def.make_track()
        build_rails(base.loader, self.world, self.track)

        self.cart = NodePath("cart")
        self.cart.reparentTo(self.world)
        build_cart(base.loader, self.cart)

        self.camera_pivot = NodePath("camera_pivot")
        self.camera_pivot.reparentTo(self.cart)
        self.camera_pivot.setPos(0, 0, 0)

        self._saved_cam_parent = base.camera.getParent()
        base.camera.reparentTo(self.camera_pivot)
        base.camera.setPos(0, 0, 0)
        base.camera.setHpr(0, 0, 0)
        base.camLens.setFov(90)
        base.camLens.setNear(0.2)
        base.camLens.setFar(500)

        self.cam_ctrl = CameraController(base, self.camera_pivot)

        self.spawned_horses = spawn_horses(
            base.loader, self.world, self.track, count=10, map_id=self.map_id
        )

        self._build_hud()

        speed_name = self.app.config.get("cart_speed", "normal")
        self.speed = settings.SPEED_VALUES.get(speed_name, 3.0)
        self.t_param = 0.0

        countdown = float(self.app.config.get("countdown_duration", 1.0))
        self.photo = PhotoManager(
            base=base,
            countdown_duration=countdown,
            get_depth=self.app.depth_client.get_depth,
            hud_root=self.hud_root,
            progress_setter=self._update_fill_ring,
            get_paused=lambda: self.frozen,
            get_horse_nodes=lambda: list(self.spawned_horses),
            get_map_id=lambda: self.map_id,
        )

        self._bind_inputs()
        self._has_camera_state = True

        cart_audio = asset_gen.audio_path("minecart_loop.ogg")
        if cart_audio is not None:
            try:
                self._cart_sfx = base.loader.loadSfx(Filename.fromOsSpecific(str(cart_audio)))
                if self._cart_sfx is not None:
                    self._cart_sfx.setLoop(True)
                    self._cart_sfx.play()
            except Exception:
                self._cart_sfx = None

        wave_audio = asset_gen.audio_path("wave_emote.wav")
        if wave_audio is not None:
            try:
                self._wave_sfx = base.loader.loadSfx(Filename.fromOsSpecific(str(wave_audio)))
            except Exception:
                self._wave_sfx = None

    def _build_environment(self) -> None:
        if self.map_id == "desert":
            self._build_ground(asset_gen.sand_path(),
                               fallback=Vec4(0.78, 0.65, 0.45, 1.0),
                               size=DESERT_GROUND_SIZE, tile=60)
            self._build_sky(asset_gen.desert_sky_path(),
                            fallback=Vec4(0.95, 0.78, 0.55, 1.0))
            self._mountains = build_mountains(self.world)
            scatter_bushes(self.app.base.loader, self.world)
            self._setup_lights(
                ambient=Vec4(0.62, 0.55, 0.42, 1),
                dir_color=Vec4(0.95, 0.85, 0.65, 1),
                dir_hpr=Vec3(60, -30, 0),
            )
        else:
            self._build_ground(asset_gen.grass_path(),
                               fallback=Vec4(0.20, 0.55, 0.25, 1.0),
                               size=GROUND_SIZE, tile=30)
            self._build_sky(asset_gen.sky_path(),
                            fallback=Vec4(0.5, 0.75, 0.95, 1.0))
            self._setup_lights(
                ambient=Vec4(0.55, 0.55, 0.60, 1),
                dir_color=Vec4(0.85, 0.82, 0.75, 1),
                dir_hpr=Vec3(45, -45, 0),
            )

    def _build_ground(self, tex_path: Optional[Path], fallback: Vec4,
                      size: float, tile: int) -> None:
        base = self.app.base
        cm = CardMaker("ground")
        cm.setFrame(-size / 2, size / 2, -size / 2, size / 2)
        ground = self.world.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setZ(0)
        if tex_path is not None:
            try:
                tex = base.loader.loadTexture(Filename.fromOsSpecific(str(tex_path)))
                tex.setMagfilter(SamplerState.FT_nearest)
                tex.setMinfilter(SamplerState.FT_nearest)
                tex.setWrapU(SamplerState.WM_repeat)
                tex.setWrapV(SamplerState.WM_repeat)
                ground.setTexture(tex)
                ground.setTexScale(TextureStage.getDefault(), tile, tile)
            except Exception:
                ground.setColor(fallback)
        else:
            ground.setColor(fallback)

    def _build_sky(self, tex_path: Optional[Path], fallback: Vec4) -> None:
        base = self.app.base
        sky_cm = CardMaker("sky")
        sky_cm.setFrame(-1, 1, -1, 1)
        sky = base.render2dp.attachNewNode(sky_cm.generate())
        sky.setColor(fallback)
        base.cam2dp.node().getDisplayRegion(0).setSort(-20)
        if tex_path is not None:
            try:
                stex = base.loader.loadTexture(Filename.fromOsSpecific(str(tex_path)))
                stex.setMagfilter(SamplerState.FT_nearest)
                stex.setMinfilter(SamplerState.FT_nearest)
                sky.setTexture(stex)
            except Exception:
                pass
        self._sky_card = sky

    def _setup_lights(self, ambient: Vec4, dir_color: Vec4, dir_hpr: Vec3) -> None:
        amb = AmbientLight("ambient")
        amb.setColor(ambient)
        amb_np = self.world.attachNewNode(amb)
        self.world.setLight(amb_np)
        self._lights.append(amb_np)

        directional = DirectionalLight("directional")
        directional.setColor(dir_color)
        dir_np = self.world.attachNewNode(directional)
        dir_np.setHpr(dir_hpr)
        self.world.setLight(dir_np)
        self._lights.append(dir_np)

    def _build_hud(self) -> None:
        base = self.app.base
        self.hud_root = NodePath("hud_root")
        self.hud_root.reparentTo(base.aspect2d)

        shadow = self._make_reticle(Vec4(0, 0, 0, 1), shift=0.0035)
        shadow.reparentTo(self.hud_root)
        cross = self._make_reticle(Vec4(1, 1, 1, 1), shift=0.0)
        cross.reparentTo(self.hud_root)

        self.fill_ring_node = NodePath("fill_ring")
        self.fill_ring_node.reparentTo(self.hud_root)
        self.fill_ring_node.hide()

    def _make_reticle(self, color: Vec4, shift: float) -> NodePath:
        ls = LineSegs()
        ls.setThickness(2.0)
        ls.setColor(color)
        sx, sy = shift, -shift
        ls.moveTo(sx + RETICLE_GAP, 0, sy)
        ls.drawTo(sx + RETICLE_HALF, 0, sy)
        ls.moveTo(sx - RETICLE_GAP, 0, sy)
        ls.drawTo(sx - RETICLE_HALF, 0, sy)
        ls.moveTo(sx, 0, sy + RETICLE_GAP)
        ls.drawTo(sx, 0, sy + RETICLE_HALF)
        ls.moveTo(sx, 0, sy - RETICLE_GAP)
        ls.drawTo(sx, 0, sy - RETICLE_HALF)
        node = ls.create()
        return NodePath(node)

    def _update_fill_ring(self, progress: float) -> None:
        if self.fill_ring_node is None:
            return
        for child in self.fill_ring_node.getChildren():
            child.removeNode()
        if progress <= 0.0:
            self.fill_ring_node.hide()
            return
        self.fill_ring_node.show()
        progress = max(0.0, min(1.0, progress))
        green = Vec4(0.30, 0.85, 0.30, 1.0)
        yellow = Vec4(0.95, 0.85, 0.20, 1.0)
        col = green + (yellow - green) * progress
        ls = LineSegs()
        ls.setThickness(3.0)
        ls.setColor(col)
        n = max(1, int(FILL_RING_SEGMENTS * progress))
        end_angle = 2.0 * math.pi * progress
        start_angle = -math.pi / 2.0
        for i in range(n + 1):
            a = start_angle + (end_angle * i / n)
            x = math.cos(a) * FILL_RING_RADIUS
            z = math.sin(a) * FILL_RING_RADIUS
            if i == 0:
                ls.moveTo(x, 0, z)
            else:
                ls.drawTo(x, 0, z)
        node = ls.create()
        NodePath(node).reparentTo(self.fill_ring_node)

    def _bind_inputs(self) -> None:
        base = self.app.base
        trigger = self.app.config.get("photo_trigger", "left_click")

        if trigger == "left_click":
            press, release = "mouse1", "mouse1-up"
        elif trigger == "right_click":
            press, release = "mouse3", "mouse3-up"
        else:
            press, release = "space", "space-up"

        base.accept(press, self._on_trigger_press)
        base.accept(release, self._on_trigger_release)
        base.accept("wheel_up", self._on_wave)
        self._accept_keys.extend([press, release, "wheel_up"])

    def _unbind_inputs(self) -> None:
        base = self.app.base
        for k in self._accept_keys:
            base.ignore(k)
        self._accept_keys = []

    def refresh_settings(self) -> None:
        self._unbind_inputs()
        self._bind_inputs()
        speed_name = self.app.config.get("cart_speed", "normal")
        self.speed = settings.SPEED_VALUES.get(speed_name, 3.0)
        if self.photo is not None:
            self.photo.countdown_duration = float(
                self.app.config.get("countdown_duration", 1.0)
            )

    def on_escape(self) -> None:
        self.app.scene_manager.push_overlay("pause")

    def _on_trigger_press(self) -> None:
        if self.photo is not None and not self.frozen:
            self.photo.set_trigger_held(True)

    def _on_trigger_release(self) -> None:
        if self.photo is not None:
            self.photo.set_trigger_held(False)

    def _on_wave(self) -> None:
        if self.frozen or self._wave_cooldown > 0.0 or self.hud_root is None:
            return
        if self.photo is not None and self.photo.state in (
            PhotoState.HOLDING,
            PhotoState.FLASHING,
        ):
            return

        self._destroy_wave_label()
        self._wave_label = DirectLabel(
            parent=self.hud_root,
            text="WAVE!",
            text_fg=Vec4(WAVE_TEXT_RGB[0], WAVE_TEXT_RGB[1], WAVE_TEXT_RGB[2], 0.0),
            text_scale=WAVE_SCALE_START,
            text_font=self.app.font,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.18),
        )
        self._wave_state = "in"
        self._wave_elapsed = 0.0
        self._wave_cooldown = WAVE_COOLDOWN
        if self._wave_sfx is not None:
            try:
                self._wave_sfx.play()
            except Exception:
                pass

    def _tick_wave(self, dt: float) -> None:
        if self._wave_state == "idle" or self._wave_label is None:
            return
        self._wave_elapsed += dt

        if self._wave_state == "in":
            t = min(1.0, self._wave_elapsed / WAVE_FADE_IN)
            ease = 1.0 - (1.0 - t) * (1.0 - t)
            self._set_wave_alpha(ease)
            self._wave_label["text_scale"] = (
                WAVE_SCALE_START + (WAVE_SCALE_END - WAVE_SCALE_START) * ease
            )
            if t >= 1.0:
                self._wave_state = "hold"
                self._wave_elapsed = 0.0
            return

        if self._wave_state == "hold":
            if self._wave_elapsed >= WAVE_HOLD:
                self._wave_state = "out"
                self._wave_elapsed = 0.0
            return

        if self._wave_state == "out":
            t = min(1.0, self._wave_elapsed / WAVE_FADE_OUT)
            self._set_wave_alpha(1.0 - t)
            if t >= 1.0:
                self._destroy_wave_label()
                self._wave_state = "idle"
                self._wave_elapsed = 0.0

    def _set_wave_alpha(self, alpha: float) -> None:
        if self._wave_label is None:
            return
        a = max(0.0, min(1.0, alpha))
        self._wave_label["text_fg"] = Vec4(WAVE_TEXT_RGB[0], WAVE_TEXT_RGB[1], WAVE_TEXT_RGB[2], a)

    def _destroy_wave_label(self) -> None:
        if self._wave_label is not None:
            try:
                self._wave_label.destroy()
            except Exception:
                pass
            self._wave_label = None

    def update(self, dt: float) -> None:
        if self._wave_cooldown > 0.0:
            self._wave_cooldown = max(0.0, self._wave_cooldown - dt)
        self._tick_wave(dt)

        if self.frozen:
            return
        if self.track is None or self.cart is None:
            return
        cart_frozen = self.photo is not None and self.photo.state in (
            PhotoState.HOLDING,
            PhotoState.FLASHING,
        )
        if not cart_frozen:
            self.t_param = self.track.advance(self.t_param, self.speed, dt)
        pos, tangent = self.track.evaluate(self.t_param)
        self.cart.setPos(pos)
        self.cart.lookAt(pos + tangent)
        if self.cam_ctrl is not None and not cart_frozen:
            self.cam_ctrl.update(dt)
        if self.photo is not None:
            self.photo.tick(dt)

    def exit(self) -> None:
        self._unbind_inputs()
        if self._cart_sfx is not None:
            try:
                self._cart_sfx.stop()
            except Exception:
                pass
            self._cart_sfx = None
        if self._wave_sfx is not None:
            try:
                self._wave_sfx.stop()
            except Exception:
                pass
            self._wave_sfx = None
        self._destroy_wave_label()
        self._wave_state = "idle"
        self._wave_elapsed = 0.0
        self._wave_cooldown = 0.0
        if self.photo is not None:
            self.photo.cleanup()
            self.photo = None

        base = self.app.base
        if self._has_camera_state and self._saved_cam_parent is not None:
            base.camera.reparentTo(self._saved_cam_parent)
            base.camera.setPos(0, 0, 0)
            base.camera.setHpr(0, 0, 0)
            base.camLens.setFov(90)
            self._has_camera_state = False
            self._saved_cam_parent = None

        if self.hud_root is not None:
            self.hud_root.removeNode()
            self.hud_root = None
        if hasattr(self, "_sky_card") and self._sky_card is not None:
            self._sky_card.removeNode()
            self._sky_card = None
        if self._mountains is not None:
            self._mountains.removeNode()
            self._mountains = None
        if self.world is not None:
            self.world.removeNode()
            self.world = None
        self.cart = None
        self.camera_pivot = None
        self.fill_ring_node = None
        self.track = None
        self.spawned_horses = []
        self._lights = []
