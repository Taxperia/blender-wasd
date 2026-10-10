# SPDX-License-Identifier: GPL-3.0-or-later

"""GameNav - game-style viewport navigation for Blender."""

import math
import time

import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    PointerProperty,
)
from mathutils import Vector


bl_info = {
    "name": "GameNav",
    "author": "Talba",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > GameNav",
    "description": "Navigate large Blender scenes with game-style WASD controls",
    "category": "3D View",
}


addon_keymaps = []


def addon_preferences(context):
    """Return this extension's preferences in legacy and extension installs."""
    addon = context.preferences.addons.get(__package__)
    if addon is None:
        addon = context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


class GAMENAV_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    base_speed: FloatProperty(
        name="Temel Hız",
        description="Normal hareket hızı (Blender birimi / saniye)",
        default=8.0,
        min=0.01,
        soft_max=500.0,
        max=100000.0,
        precision=2,
    )
    sprint_multiplier: FloatProperty(
        name="Koşma Çarpanı",
        description="Shift basılıyken hız çarpanı",
        default=5.0,
        min=1.0,
        soft_max=10.0,
        max=50.0,
        precision=1,
    )
    precision_multiplier: FloatProperty(
        name="Yavaş Hareket Çarpanı",
        description="Alt basılıyken kullanılan hız oranı",
        default=0.2,
        min=0.01,
        max=1.0,
        precision=2,
    )
    mouse_sensitivity: FloatProperty(
        name="Mouse Hassasiyeti",
        description="Mouse ile bakış hassasiyeti",
        default=0.0025,
        min=0.0001,
        max=0.02,
        precision=4,
    )
    smooth_movement: BoolProperty(
        name="Yumuşak Hareket",
        description="Başlama ve durmayı yumuşat",
        default=True,
    )
    acceleration: FloatProperty(
        name="Yumuşaklık",
        description="Yüksek değer hedef hıza daha çabuk ulaşır",
        default=12.0,
        min=1.0,
        max=40.0,
        precision=1,
    )
    ground_mode: BoolProperty(
        name="Yatay WASD",
        description="WASD hareketini zemine paralel tut; E ve Q dikey hareket eder",
        default=False,
    )
    invert_y: BoolProperty(
        name="Dikey Bakışı Ters Çevir",
        description="Mouse yukarı/aşağı bakış yönünü ters çevir",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Hareket")
        layout.prop(self, "base_speed")
        layout.prop(self, "sprint_multiplier")
        layout.prop(self, "precision_multiplier")
        layout.separator()
        layout.label(text="Bakış ve Hissediliş")
        layout.prop(self, "mouse_sensitivity")
        layout.prop(self, "invert_y")
        layout.prop(self, "ground_mode")
        layout.prop(self, "smooth_movement")
        if self.smooth_movement:
            layout.prop(self, "acceleration")


class GAMENAV_SceneState(bpy.types.PropertyGroup):
    home_valid: BoolProperty(default=False, options={'HIDDEN'})
    home_location: FloatVectorProperty(size=3, subtype='XYZ')
    home_rotation: FloatVectorProperty(size=4, subtype='QUATERNION', default=(1.0, 0.0, 0.0, 0.0))
    home_distance: FloatProperty(default=10.0, min=0.0)


class GAMENAV_OT_navigate(bpy.types.Operator):
    bl_idname = "view3d.gamenav_navigate"
    bl_label = "GameNav Başlat"
    bl_description = "Oyun tarzı WASD gezinmeyi başlat (Shift+F)"
    bl_options = {'BLOCKING'}

    _timer = None
    _keys = None
    _velocity = None

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.region is not None
            and context.region.type == 'WINDOW'
            and context.region_data is not None
        )

    def invoke(self, context, event):
        prefs = addon_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "GameNav tercihleri bulunamadı")
            return {'CANCELLED'}

        rv3d = context.region_data
        self._rv3d = rv3d
        self._area = context.area
        self._window = context.window
        self._wm = context.window_manager
        self._original_location = rv3d.view_location.copy()
        self._original_rotation = rv3d.view_rotation.copy()
        self._original_distance = rv3d.view_distance
        self._original_perspective = rv3d.view_perspective

        # Camera view should not accidentally move the scene camera.
        if rv3d.view_perspective == 'CAMERA':
            rv3d.view_perspective = 'PERSP'

        forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
        self._yaw = math.atan2(forward.y, forward.x)
        self._pitch = math.asin(max(-1.0, min(1.0, forward.z)))

        self._base_speed = prefs.base_speed
        self._session_speed = prefs.base_speed
        self._sprint_multiplier = prefs.sprint_multiplier
        self._precision_multiplier = prefs.precision_multiplier
        self._mouse_sensitivity = prefs.mouse_sensitivity
        self._smooth_movement = prefs.smooth_movement
        self._acceleration = prefs.acceleration
        self._ground_mode = prefs.ground_mode
        self._invert_y = prefs.invert_y

        self._keys = set()
        self._velocity = Vector((0.0, 0.0, 0.0))
        self._last_time = time.perf_counter()
        self._center_x = context.region.x + context.region.width // 2
        self._center_y = context.region.y + context.region.height // 2

        self._timer = self._wm.event_timer_add(1.0 / 60.0, window=self._window)
        self._wm.modal_handler_add(self)
        self._window.cursor_modal_set('NONE')
        self._window.cursor_warp(self._center_x, self._center_y)
        self._set_status(context)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self._area is None or self._area.type != 'VIEW_3D':
            self._cleanup(context)
            return {'CANCELLED'}

        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._restore_original_view()
            self._cleanup(context)
            return {'CANCELLED'}

        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            self._cleanup(context)
            return {'FINISHED'}

        movement_keys = {
            'W', 'A', 'S', 'D', 'E', 'Q',
            'UP_ARROW', 'DOWN_ARROW', 'LEFT_ARROW', 'RIGHT_ARROW',
            'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_ALT', 'RIGHT_ALT',
        }
        if event.type in movement_keys:
            if event.value == 'PRESS':
                self._keys.add(event.type)
            elif event.value == 'RELEASE':
                self._keys.discard(event.type)
            return {'RUNNING_MODAL'}

        if event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            self._session_speed = min(100000.0, self._session_speed * 1.25)
            self._set_status(context)
            return {'RUNNING_MODAL'}

        if event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            self._session_speed = max(0.01, self._session_speed / 1.25)
            self._set_status(context)
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self._look(event)
            return {'RUNNING_MODAL'}

        # Blender 5.1 no longer exposes the originating timer on Event.
        # The timer is attached to this operator's window, so TIMER is enough.
        if event.type == 'TIMER':
            self._move()
            self._area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def _look(self, event):
        dx = event.mouse_x - self._center_x
        dy = event.mouse_y - self._center_y
        if dx == 0 and dy == 0:
            return

        self._yaw -= dx * self._mouse_sensitivity
        y_sign = -1.0 if self._invert_y else 1.0
        self._pitch += dy * self._mouse_sensitivity * y_sign
        limit = math.radians(89.5)
        self._pitch = max(-limit, min(limit, self._pitch))

        cos_pitch = math.cos(self._pitch)
        forward = Vector((
            cos_pitch * math.cos(self._yaw),
            cos_pitch * math.sin(self._yaw),
            math.sin(self._pitch),
        ))
        self._rv3d.view_rotation = forward.to_track_quat('-Z', 'Y')
        self._window.cursor_warp(self._center_x, self._center_y)
        self._area.tag_redraw()

    def _move(self):
        now = time.perf_counter()
        dt = min(0.05, max(0.0, now - self._last_time))
        self._last_time = now

        rotation = self._rv3d.view_rotation
        forward = rotation @ Vector((0.0, 0.0, -1.0))
        right = rotation @ Vector((1.0, 0.0, 0.0))
        up = Vector((0.0, 0.0, 1.0))

        if self._ground_mode:
            forward.z = 0.0
            right.z = 0.0
            if forward.length_squared > 0.0:
                forward.normalize()
            if right.length_squared > 0.0:
                right.normalize()

        direction = Vector((0.0, 0.0, 0.0))
        if self._pressed('W', 'UP_ARROW'):
            direction += forward
        if self._pressed('S', 'DOWN_ARROW'):
            direction -= forward
        if self._pressed('D', 'RIGHT_ARROW'):
            direction += right
        if self._pressed('A', 'LEFT_ARROW'):
            direction -= right
        if self._pressed('E'):
            direction += up
        if self._pressed('Q'):
            direction -= up

        if direction.length_squared > 0.0:
            direction.normalize()

        speed = self._session_speed
        if self._pressed('LEFT_SHIFT', 'RIGHT_SHIFT'):
            speed *= self._sprint_multiplier
        if self._pressed('LEFT_ALT', 'RIGHT_ALT'):
            speed *= self._precision_multiplier

        target_velocity = direction * speed
        if self._smooth_movement:
            blend = 1.0 - math.exp(-self._acceleration * dt)
            self._velocity += (target_velocity - self._velocity) * blend
        else:
            self._velocity = target_velocity

        if self._velocity.length_squared > 1.0e-10:
            self._rv3d.view_location += self._velocity * dt

    def _pressed(self, *keys):
        return any(key in self._keys for key in keys)

    def _set_status(self, context):
        text = (
            f"GameNav | WASD: hareket  E/Q: yukarı/aşağı  Shift: hızlan  "
            f"Alt: yavaşla  Tekerlek: hız ({self._session_speed:.2f})  "
            "Sol Tık/Enter: bitir  Esc/Sağ Tık: iptal"
        )
        context.workspace.status_text_set(text)

    def _restore_original_view(self):
        self._rv3d.view_location = self._original_location
        self._rv3d.view_rotation = self._original_rotation
        self._rv3d.view_distance = self._original_distance
        self._rv3d.view_perspective = self._original_perspective

    def _cleanup(self, context):
        if self._timer is not None:
            self._wm.event_timer_remove(self._timer)
            self._timer = None
        try:
            self._window.cursor_modal_restore()
        except RuntimeError:
            pass
        try:
            context.workspace.status_text_set(None)
        except (AttributeError, RuntimeError):
            pass
        if self._area is not None:
            self._area.tag_redraw()


class GAMENAV_OT_speed_preset(bpy.types.Operator):
    bl_idname = "view3d.gamenav_speed_preset"
    bl_label = "Hız Profili"
    bl_description = "GameNav hız profilini değiştir"
    bl_options = {'INTERNAL'}

    speed: FloatProperty(min=0.01, max=100000.0)
    sprint: FloatProperty(min=1.0, max=50.0)

    def execute(self, context):
        prefs = addon_preferences(context)
        if prefs is None:
            return {'CANCELLED'}
        prefs.base_speed = self.speed
        prefs.sprint_multiplier = self.sprint
        return {'FINISHED'}


class GAMENAV_OT_focus_selected(bpy.types.Operator):
    bl_idname = "view3d.gamenav_focus_selected"
    bl_label = "Seçilene Git"
    bl_description = "Görünümü seçili nesne veya bileşenlere odakla"

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        if not context.selected_objects and context.mode == 'OBJECT':
            self.report({'WARNING'}, "Önce bir nesne seç")
            return {'CANCELLED'}
        return bpy.ops.view3d.view_selected('EXEC_DEFAULT', use_all_regions=False)


class GAMENAV_OT_large_scene_clipping(bpy.types.Operator):
    bl_idname = "view3d.gamenav_large_scene_clipping"
    bl_label = "Büyük Sahne Görüşü"
    bl_description = "3D görünüm uzak kırpma mesafesini 10 milyon birime çıkar"

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        context.space_data.clip_end = max(context.space_data.clip_end, 10_000_000.0)
        context.space_data.clip_start = max(context.space_data.clip_start, 0.1)
        self.report({'INFO'}, "Görüş mesafesi büyük sahneler için ayarlandı")
        return {'FINISHED'}


class GAMENAV_OT_save_home(bpy.types.Operator):
    bl_idname = "view3d.gamenav_save_home"
    bl_label = "Konumu Kaydet"
    bl_description = "Mevcut görünümü bu .blend dosyasına ana konum olarak kaydet"

    @classmethod
    def poll(cls, context):
        return context.region_data is not None

    def execute(self, context):
        state = context.scene.gamenav_state
        rv3d = context.region_data
        state.home_location = rv3d.view_location
        state.home_rotation = rv3d.view_rotation
        state.home_distance = rv3d.view_distance
        state.home_valid = True
        self.report({'INFO'}, "GameNav ana konumu kaydedildi")
        return {'FINISHED'}


class GAMENAV_OT_go_home(bpy.types.Operator):
    bl_idname = "view3d.gamenav_go_home"
    bl_label = "Kayıtlı Konuma Dön"
    bl_description = "Kaydedilmiş GameNav ana konumuna dön"

    @classmethod
    def poll(cls, context):
        return (
            context.region_data is not None
            and hasattr(context.scene, "gamenav_state")
            and context.scene.gamenav_state.home_valid
        )

    def execute(self, context):
        state = context.scene.gamenav_state
        rv3d = context.region_data
        rv3d.view_perspective = 'PERSP'
        rv3d.view_location = state.home_location
        rv3d.view_rotation = state.home_rotation
        rv3d.view_distance = state.home_distance
        context.area.tag_redraw()
        return {'FINISHED'}


class GAMENAV_PT_panel(bpy.types.Panel):
    bl_label = "GameNav"
    bl_idname = "GAMENAV_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GameNav"

    def draw(self, context):
        layout = self.layout
        prefs = addon_preferences(context)

        start = layout.row()
        start.scale_y = 1.6
        start.operator("view3d.gamenav_navigate", text="WASD Gezinmeyi Başlat", icon='PLAY')
        layout.label(text="Kısayol: Shift + F", icon='EVENT_F')

        if prefs is None:
            layout.label(text="Tercihler yüklenemedi", icon='ERROR')
            return

        box = layout.box()
        box.label(text="Hız Profili", icon='DRIVER')
        row = box.row(align=True)
        op = row.operator("view3d.gamenav_speed_preset", text="Oda")
        op.speed, op.sprint = 3.0, 4.0
        op = row.operator("view3d.gamenav_speed_preset", text="Sahne")
        op.speed, op.sprint = 25.0, 6.0
        op = row.operator("view3d.gamenav_speed_preset", text="Mega")
        op.speed, op.sprint = 250.0, 10.0
        box.prop(prefs, "base_speed")
        box.prop(prefs, "sprint_multiplier")
        box.prop(prefs, "mouse_sensitivity")
        box.prop(prefs, "ground_mode")

        box = layout.box()
        box.label(text="Hızlı Erişim", icon='VIEW3D')
        box.operator("view3d.gamenav_focus_selected", icon='ZOOM_SELECTED')
        box.operator("view3d.gamenav_large_scene_clipping", icon='XRAY')
        row = box.row(align=True)
        row.operator("view3d.gamenav_save_home", text="Konumu Kaydet", icon='BOOKMARKS')
        row.operator("view3d.gamenav_go_home", text="Geri Dön", icon='LOOP_BACK')

        help_box = layout.box()
        help_box.label(text="Kontroller", icon='QUESTION')
        help_box.label(text="W A S D / Oklar  •  Hareket")
        help_box.label(text="Mouse  •  Bakış")
        help_box.label(text="E / Q  •  Yukarı / Aşağı")
        help_box.label(text="Shift / Alt  •  Hızlı / Yavaş")
        help_box.label(text="Tekerlek  •  Anlık hız")
        help_box.label(text="Sol tık: Bitir  •  Esc: İptal")


def draw_view_navigation_menu(self, context):
    self.layout.separator()
    self.layout.operator(GAMENAV_OT_navigate.bl_idname, icon='PLAY')


classes = (
    GAMENAV_Preferences,
    GAMENAV_SceneState,
    GAMENAV_OT_navigate,
    GAMENAV_OT_speed_preset,
    GAMENAV_OT_focus_selected,
    GAMENAV_OT_large_scene_clipping,
    GAMENAV_OT_save_home,
    GAMENAV_OT_go_home,
    GAMENAV_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.gamenav_state = PointerProperty(type=GAMENAV_SceneState)

    menu = getattr(bpy.types, "VIEW3D_MT_view_navigation", None)
    if menu is not None:
        menu.append(draw_view_navigation_menu)

    wm = bpy.context.window_manager
    keyconfig = wm.keyconfigs.addon if wm else None
    if keyconfig is not None:
        keymap = keyconfig.keymaps.new(name='3D View', space_type='VIEW_3D', region_type='WINDOW')
        item = keymap.keymap_items.new(
            GAMENAV_OT_navigate.bl_idname,
            type='F',
            value='PRESS',
            shift=True,
        )
        addon_keymaps.append((keymap, item))


def unregister():
    for keymap, item in addon_keymaps:
        keymap.keymap_items.remove(item)
    addon_keymaps.clear()

    menu = getattr(bpy.types, "VIEW3D_MT_view_navigation", None)
    if menu is not None:
        menu.remove(draw_view_navigation_menu)

    if hasattr(bpy.types.Scene, "gamenav_state"):
        del bpy.types.Scene.gamenav_state

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
