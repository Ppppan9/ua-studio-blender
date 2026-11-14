"""⑤ 物理库 II：布料（旗帜/桌布）/ 果冻（布料气压）/ 绳索摆挂。

果冻用「闭合网格 + 布料气压」的经典配方，效果稳定；
绳索用窄布条顶部钉住 + 初始摆角，天然形成钟摆运动。
"""

from __future__ import annotations

import math

import bpy

from . import util

GROUND_FALLBACK = 0.22


def _ground_z() -> float:
    if bpy.data.objects.get("UA_Stage_Podium") is not None:
        return 0.22
    if bpy.data.objects.get("UA_Stage_Desk") is not None:
        return 0.70
    return 0.0


def _make_stage_collision(context) -> int:
    """给舞台体加碰撞修饰器（布料/软体专用）。"""
    n = 0
    for name in ("UA_Stage_Podium", "UA_Stage_Desk", "UA_Stage_Floor"):
        obj = util.find_object(name)
        if obj is None:
            continue
        if obj.modifiers.get("UA_Collision") is None:
            obj.modifiers.new("UA_Collision", "COLLISION")
        n += 1
    return n


def _pin_group(obj, side: str) -> bpy.types.VertexGroup:
    """按网格局部坐标选出边缘顶点做钉住组。side: x_min/x_max/y_min/y_max。"""
    vg = obj.vertex_groups.new(name="UA_Pin")
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    eps = 0.01
    targets = []
    if side == "x_min":
        targets = [v.index for v in obj.data.vertices if abs(v.co.x - min(xs)) < eps]
    elif side == "x_max":
        targets = [v.index for v in obj.data.vertices if abs(v.co.x - max(xs)) < eps]
    elif side == "y_min":
        targets = [v.index for v in obj.data.vertices if abs(v.co.y - min(ys)) < eps]
    elif side == "y_max":
        targets = [v.index for v in obj.data.vertices if abs(v.co.y - max(ys)) < eps]
    if targets:
        vg.add(targets, 1.0, "REPLACE")
    return vg


def _cloth_mod(obj, pin_vg=None, quality: int = 6):
    mod = obj.modifiers.new("UA_Cloth", "CLOTH")
    st = mod.settings
    st.quality = quality
    st.mass = 0.25
    if pin_vg is not None:
        st.vertex_group_mass = pin_vg.name
    return mod


def _finish_fx(context, obj, name) -> None:
    obj.name = name
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(obj, coll)


def make_flag(context) -> bpy.types.Object:
    """旗帜：网格布面钉在旗杆上 + 风力场。"""
    _make_stage_collision(context)
    ground = _ground_z()

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=24, y_subdivisions=18, size=1.4,
        align="WORLD", location=(0, 0, ground + 1.5),
    )
    cloth = context.active_object
    cloth.rotation_euler.x = math.radians(90)

    vg = _pin_group(cloth, "x_min")
    _cloth_mod(cloth, vg, quality=8)
    _finish_fx(context, cloth, "UA_Flag")

    # 旗杆（视觉 + 钉住边的位置参考）
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.035, depth=2.6, vertices=24,
        align="WORLD", location=(-0.7, 0, ground + 1.3),
    )
    pole = context.active_object
    _finish_fx(context, pole, "UA_FlagPole")

    # 风力场
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.mesh.primitive_plane_add(size=0.1, align="WORLD",
                                     location=(-3.0, 0, ground + 2.0))
    fan = context.active_object
    bpy.ops.object.forcefield_toggle()
    fan.field.type = "WIND"
    fan.field.strength = 25.0
    fan.rotation_euler.y = math.radians(90)
    fan.hide_render = True
    _finish_fx(context, fan, "UA_Wind")
    return cloth


def make_tablecloth(context) -> bpy.types.Object:
    """桌布：布料从空中落到舞台/桌面上铺开。"""
    _make_stage_collision(context)
    top = _ground_z()

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=32, y_subdivisions=32, size=2.4,
        align="WORLD", location=(0, 0, top + 1.2),
    )
    cloth = context.active_object
    _cloth_mod(cloth, None, quality=8)
    _finish_fx(context, cloth, "UA_Tablecloth")
    return cloth


def make_jelly(context) -> bpy.types.Object:
    """果冻：闭合球体 + 布料气压，落地 Q 弹。"""
    _make_stage_collision(context)
    ground = _ground_z()

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.4, segments=48, ring_count=24,
        align="WORLD", location=(0, 0, ground + 1.6),
    )
    jelly = context.active_object
    mod = _cloth_mod(jelly, None, quality=7)
    try:
        mod.settings.use_pressure = True
        mod.settings.uniform_pressure = 2.0
    except AttributeError:
        pass
    _finish_fx(context, jelly, "UA_Jelly")
    return jelly


def make_rope(context) -> bpy.types.Object:
    """绳索摆挂：窄布条钉住顶端，初始摆角形成钟摆。"""
    _make_stage_collision(context)
    ground = _ground_z()

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=4, y_subdivisions=28, size=1.0,
        align="WORLD", location=(0, 0, ground + 1.8),
    )
    rope = context.active_object
    rope.rotation_euler.x = math.radians(90)
    rope.scale = (0.15, 1.3, 1.0)

    # 顶端一行钉住（局部 y_max 在旋转后位于上方）
    vg = _pin_group(rope, "y_max")
    _cloth_mod(rope, vg, quality=8)
    # 初始摆角
    rope.rotation_euler.y = math.radians(25)
    _finish_fx(context, rope, "UA_Rope")
    return rope


def cloth_on_selected(context) -> int:
    """把选中物体变成布料（掉落到舞台上演示布料效果）。"""
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs:
        raise ValueError("请先选中物体")
    _make_stage_collision(context)
    for obj in objs:
        _cloth_mod(obj, None, quality=6)
    return len(objs)
