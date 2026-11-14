"""工程模块：一键新建买量工程 / 背景 / 舞台 / 灯光 / 尺寸。

全部函数以 context + scene.uastudio（属性组）为输入，
Operator 层只做薄封装与撤销/报告。
"""

from __future__ import annotations

import bpy

from . import util


# ---------------------------------------------------------------------------
# 尺寸
# ---------------------------------------------------------------------------


def apply_size(context, props) -> None:
    """应用比例/帧率/片长；若已有 UA 相机则同步机位。"""
    scene = context.scene
    util.set_resolution(scene, props.aspect)
    util.set_fps(scene, props.fps)
    util.set_duration(scene, props.duration)
    _ensure_camera(context, props.aspect)


# ---------------------------------------------------------------------------
# 背景
# ---------------------------------------------------------------------------


def set_background(context, props) -> None:
    """按 bg_mode 重建背景：gradient/studio 用影棚穹幕，flat 用纯色世界。"""
    scene = context.scene
    if props.bg_mode == "flat":
        util.remove_backdrop()
        util.make_world_flat(scene, tuple(props.bg_bottom)[:3])
    elif props.bg_mode == "studio":
        # 影棚：中性灰穹幕，弱化环境色，靠柔光箱塑形
        util.make_backdrop(scene, (0.05, 0.05, 0.06), (0.55, 0.55, 0.58))
        util.make_world_flat(scene, (0.05, 0.05, 0.06))
    else:  # gradient
        util.make_backdrop(
            scene, tuple(props.bg_top)[:3], tuple(props.bg_bottom)[:3]
        )
        # 穹幕外兜底：纯底部色世界
        util.make_world_flat(scene, tuple(props.bg_bottom)[:3])


# ---------------------------------------------------------------------------
# 舞台
# ---------------------------------------------------------------------------


def _stage_ops_kwargs() -> dict:
    """统一的对齐设置：以世界原点为中心。"""
    return {"align": "WORLD", "location": (0, 0, 0)}


def set_stage(context, props) -> None:
    """按 stage_kind 重建舞台（先清空 UA_Stage 集合）。"""
    _clear_stage(context)
    mat = util.get_or_make_stage_material()
    kwargs = _stage_ops_kwargs()

    kind = props.stage
    if kind == "podium":
        bpy.ops.mesh.primitive_cylinder_add(
            radius=2.2, depth=0.22, vertices=96, **kwargs
        )
        pod = context.active_object
        pod.name = "UA_Stage_Podium"
        # 抬升使台面在 z=0.22
        pod.location.z = 0.11
        _stage_polish(pod)
        _add_mat(pod, mat)
    elif kind == "desk":
        bpy.ops.mesh.primitive_cube_add(size=1, **kwargs)
        desk = context.active_object
        desk.name = "UA_Stage_Desk"
        desk.scale = (4.4, 2.6, 0.14)
        desk.location = (0, 0, 0.63)
        _stage_polish(desk)
        _add_mat(desk, mat)
    elif kind == "floor":
        bpy.ops.mesh.primitive_plane_add(size=40, **kwargs)
        floor = context.active_object
        floor.name = "UA_Stage_Floor"
        _add_mat(floor, mat)


def _clear_stage(context) -> None:
    coll = util.ensure_collection(context, "UA_Stage")
    util.clear_collection_objects(coll)


def _add_mat(obj, mat) -> None:
    util.assign_material(obj, mat)


def _stage_polish(obj) -> None:
    """舞台体统一收尾：平滑着色 + 轻倒角 + 归位到 UA_Stage 集合。"""
    # 4.1+ 无 Object.shade_smooth，用多边形级平滑
    if hasattr(obj.data, "polygons"):
        for poly in obj.data.polygons:
            poly.use_smooth = True
    bevel = obj.modifiers.new("UA_Bevel", "BEVEL")
    bevel.width = 0.015
    bevel.segments = 3
    bevel.limit_method = "ANGLE"
    util.move_to_collection(
        obj, util.ensure_collection(bpy.context, "UA_Stage")
    )


# ---------------------------------------------------------------------------
# 灯光
# ---------------------------------------------------------------------------


def _clear_lights(context) -> None:
    coll = util.ensure_collection(context, "UA_Lights")
    util.clear_collection_objects(coll)


def set_lighting(context, props) -> None:
    """按 light_mode 重建灯光组。strength 为全局强度倍率。"""
    _clear_lights(context)
    coll = util.ensure_collection(context, "UA_Lights")
    mode = props.light_mode
    if mode == "none":
        return
    s = props.light_strength

    if mode == "three_point":
        util.add_light(
            context, "UA_Light_Key", "AREA", (3.2, -3.2, 3.6),
            energy=380 * s, size=3.0, target=(0, 0, 0.5), coll=coll,
        )
        util.add_light(
            context, "UA_Light_Fill", "AREA", (-4.5, -2.5, 2.2),
            energy=140 * s, size=4.0, target=(0, 0, 0.5),
            color=(0.92, 0.95, 1.0), coll=coll,
        )
        util.add_light(
            context, "UA_Light_Rim", "AREA", (-0.5, 4.2, 3.0),
            energy=300 * s, size=2.0, target=(0, 0, 0.8), coll=coll,
        )
    elif mode == "softbox":
        util.add_light(
            context, "UA_Light_SoftTop", "AREA", (0, -1.2, 6.4),
            energy=1000 * s, size=7.0, target=(0, 0, 0), coll=coll,
        )
        util.add_light(
            context, "UA_Light_SoftL", "AREA", (-5.5, -2.0, 2.0),
            energy=260 * s, size=4.0, target=(0, 0, 0.5), coll=coll,
        )
        util.add_light(
            context, "UA_Light_SoftR", "AREA", (5.5, -2.0, 2.0),
            energy=260 * s, size=4.0, target=(0, 0, 0.5), coll=coll,
        )
    elif mode == "sky":
        # 天空光：世界 Sky Texture + 一盏补底灯
        util.make_world_sky(context.scene, strength=max(0.6, s))
        util.add_light(
            context, "UA_Light_Bounce", "AREA", (0, -3.0, 2.5),
            energy=220 * s, size=5.0, target=(0, 0, 0.5), coll=coll,
        )
        return

    # 非 sky 模式：仅当场景尚无世界时给基础环境，避免覆盖用户设置
    if context.scene.world is None:
        util.make_world_flat(context.scene, (0.06, 0.06, 0.08))


# ---------------------------------------------------------------------------
# 相机
# ---------------------------------------------------------------------------


def _ensure_camera(context, aspect_key: str) -> None:
    """创建/复位买量相机。"""
    cam = util.find_object("UA_Camera")
    if cam is None:
        coll = util.ensure_collection(context, "UA_Cameras")
        util.add_camera(context, aspect_key, coll=coll)
    else:
        loc, target = util.CAMERA_PRESETS[aspect_key]
        cam.location = loc
        util.look_at(cam, target)


# ---------------------------------------------------------------------------
# 工程
# ---------------------------------------------------------------------------


def new_project(context, props) -> None:
    """一键新建买量工程：清场景→尺寸→引擎→背景→舞台→灯光→相机。"""
    util.purge_scene(context)
    util.ensure_ua_collections(context)
    util.apply_engine(context.scene, props.engine)
    apply_size(context, props)
    set_background(context, props)
    set_stage(context, props)
    set_lighting(context, props)
    _ensure_camera(context, props.aspect)