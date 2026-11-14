"""④ 动画库：入场 / 循环 / 缓动 / 时间轴工具。

入场预设作用于选中物体，支持按顺序自动错帧（stagger）；
循环预设带 CYCLES 修饰器无限循环；缓动库直接改关键帧插值。
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from . import util

# 时间轴标记（卡点）统一前缀，便于震屏等效果识别
BEAT_PREFIX = "beat"


def _sel_meshes(context) -> list:
    objs = [o for o in context.selected_objects if o.type in {"MESH", "FONT"}]
    if not objs:
        raise ValueError("请先选中要加动画的物体")
    return objs


def _f() -> int:
    """当前帧率下 1 秒的帧数。"""
    return max(1, round(bpy.context.scene.render.fps))


def _fcurves(action):
    """遍历 Action 全部 F 曲线（兼容 4.4+ 槽位化 Action）。

    Blender 4.4 起 Action 按槽位组织，旧式 action.fcurves 在 5.x 已移除。
    """
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves
        return
    except AttributeError:
        pass
    yield from action.fcurves


def _base_state(obj) -> dict:
    """记录初始变换，动画以「当前状态」为目标位。"""
    return {
        "loc": tuple(obj.location),
        "rot": tuple(obj.rotation_euler),
        "scale": tuple(obj.scale),
    }


# ---------------------------------------------------------------------------
# 关键帧辅助
# ---------------------------------------------------------------------------


def _kf(obj, path, values, frames, interp="BEZIER") -> None:
    """逐键赋值并插入关键帧，统一插值。values 与 frames 等长。

    values 每项是该属性的完整值（location/scale 3 元组、rotation 3 元组）。
    """
    for v, f in zip(values, frames):
        if path == "location":
            obj.location = v
        elif path == "scale":
            obj.scale = v
        elif path == "rotation_euler":
            obj.rotation_euler = v
        obj.keyframe_insert(data_path=path, frame=f)
    ad = obj.animation_data
    if ad and ad.action:
        for fc in _fcurves(ad.action):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    kp.interpolation = interp


def _cycle_mod(fc) -> None:
    """给 F 曲线加 CYCLES 修饰器实现无限循环。"""
    fc.modifiers.new("CYCLES")


def _set_all_interp(obj, path: str, interp: str) -> None:
    ad = obj.animation_data
    if ad and ad.action:
        for fc in _fcurves(ad.action):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    kp.interpolation = interp


# ---------------------------------------------------------------------------
# 入场预设
# ---------------------------------------------------------------------------

ENTRANCES = ("pop", "drop", "slide", "spin")


def entrance(context, mode: str, gap: float = 0.15) -> int:
    """对选中物体加入场动画，按选中顺序自动错帧。返回处理数量。

    mode: pop(弹出) / drop(坠落弹跳) / slide(滑入) / spin(旋转飞入)
    """
    objs = _sel_meshes(context)
    scene = context.scene
    f = _f()
    t0 = scene.frame_start
    gap_f = max(1, round(gap * f))

    for i, obj in enumerate(objs):
        st = _base_state(obj)
        start = t0 + i * gap_f
        if mode == "pop":
            # 缩放 0→1，BACK 插值自带 overshoot 回弹
            obj.scale = (0.001, 0.001, 0.001)
            obj.scale = st["scale"]
            _kf(obj, "scale", [(0.001,) * 3, st["scale"]],
                [start, start + round(0.45 * f)], interp="BACK")
        elif mode == "drop":
            base_z = st["loc"][2]
            obj.location.z = base_z + 3.0
            _kf(obj, "location",
                [(st["loc"][0], st["loc"][1], base_z + 3.0), st["loc"]],
                [start, start + round(0.6 * f)], interp="BOUNCE")
        elif mode == "slide":
            base_x = st["loc"][0]
            obj.location.x = base_x - 2.5
            _kf(obj, "location",
                [(base_x - 2.5, st["loc"][1], st["loc"][2]), st["loc"]],
                [start, start + round(0.5 * f)], interp="BACK")
        elif mode == "spin":
            base_rz = st["rot"][2]
            obj.rotation_euler.z = base_rz + math.tau
            _kf(obj, "rotation_euler",
                [(st["rot"][0], st["rot"][1], base_rz + math.tau), st["rot"]],
                [start, start + round(0.7 * f)], interp="EXPO")
        _ = i
    return len(objs)


# ---------------------------------------------------------------------------
# 循环预设
# ---------------------------------------------------------------------------

LOOPS = ("float", "spin", "sway", "breath")


def loop(context, mode: str) -> int:
    """对选中物体加循环动画（CYCLES 修饰器无限循环）。"""
    objs = _sel_meshes(context)
    f = _f()
    for obj in objs:
        st = _base_state(obj)
        f0 = context.scene.frame_start
        if mode == "float":
            z0 = st["loc"][2]
            obj.location.z = z0 + 0.12
            _kf(obj, "location",
                [(st["loc"][0], st["loc"][1], z0),
                 (st["loc"][0], st["loc"][1], z0 + 0.12),
                 (st["loc"][0], st["loc"][1], z0)],
                [f0, f0 + round(0.75 * f), f0 + round(1.5 * f)],
                interp="SINE")
            for fc in _fcurves(obj.animation_data.action):
                if fc.data_path == "location":
                    _cycle_mod(fc)
        elif mode == "spin":
            base_rz = st["rot"][2]
            obj.rotation_euler.z = base_rz + math.tau
            _kf(obj, "rotation_euler",
                [(st["rot"][0], st["rot"][1], base_rz),
                 (st["rot"][0], st["rot"][1], base_rz + math.tau)],
                [f0, f0 + 4 * f], interp="LINEAR")
            for fc in _fcurves(obj.animation_data.action):
                if fc.data_path == "rotation_euler":
                    _cycle_mod(fc)
        elif mode == "sway":
            ry = st["rot"][1]
            obj.rotation_euler.y = ry + 0.15
            _kf(obj, "rotation_euler",
                [(st["rot"][0], ry, st["rot"][2]),
                 (st["rot"][0], ry + 0.15, st["rot"][2]),
                 (st["rot"][0], ry, st["rot"][2]),
                 (st["rot"][0], ry - 0.15, st["rot"][2]),
                 (st["rot"][0], ry, st["rot"][2])],
                [f0, f0 + round(0.6 * f), f0 + round(1.2 * f),
                 f0 + round(1.8 * f), f0 + round(2.4 * f)],
                interp="SINE")
            for fc in _fcurves(obj.animation_data.action):
                if fc.data_path == "rotation_euler":
                    _cycle_mod(fc)
        elif mode == "breath":
            s0 = st["scale"]
            up = tuple(c * 1.06 for c in s0)
            obj.scale = up
            _kf(obj, "scale",
                [s0, up, s0],
                [f0, f0 + round(0.6 * f), f0 + round(1.2 * f)],
                interp="SINE")
            for fc in _fcurves(obj.animation_data.action):
                if fc.data_path == "scale":
                    _cycle_mod(fc)
    return len(objs)


# ---------------------------------------------------------------------------
# 缓动库与时间轴
# ---------------------------------------------------------------------------

EASINGS = {
    "smooth": ("顺滑", "BEZIER"),
    "overshoot": ("回弹", "BACK"),
    "elastic": ("果冻弹", "ELASTIC"),
    "bounce": ("落地弹", "BOUNCE"),
    "linear": ("匀速", "LINEAR"),
}


def apply_easing(context, mode: str) -> int:
    """把选中物体已有关键帧插值一键替换。"""
    interp = EASINGS[mode][1]
    n = 0
    for obj in context.selected_objects:
        ad = obj.animation_data
        if not (ad and ad.action):
            continue
        changed = False
        for fc in _fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = interp
            changed = True
        if changed:
            n += 1
    return n


def clear_animation(context) -> int:
    """清除选中物体全部动画。"""
    objs = [o for o in context.selected_objects]
    if not objs:
        raise ValueError("请先选中物体")
    for obj in objs:
        obj.animation_data_clear()
    return len(objs)


def offset_animation(context, delta: int) -> int:
    """选中物体关键帧整体平移 delta 帧。"""
    objs = [o for o in context.selected_objects if o.animation_data]
    if not objs:
        raise ValueError("选中物体没有动画")
    for obj in objs:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.co[0] += delta
    return len(objs)


def add_beat(scene, frame: int | None = None) -> str:
    """在时间轴加卡点标记（供震屏等效果对齐）。"""
    if frame is None:
        frame = scene.frame_current
    name = f"{BEAT_PREFIX}_{frame}"
    marker = scene.timeline_markers.new(name, frame=frame)
    return marker.name


# ---------------------------------------------------------------------------
# 构图安全区（⑥）
# ---------------------------------------------------------------------------


def safety_frame(context) -> None:
    """创建顶部 UI 区 / 底部 CTA 区参考线（不参与渲染）。

    竖屏广告顶部 15% 会被平台 UI（状态栏/关闭按钮）遮挡，
    底部 18% 会被 CTA 按钮/进度条遮挡，构图时避开这两区。
    """
    scene = context.scene
    old = util.find_object("UA_SafeFrame")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    lines = []
    w = 3.2
    for z in (3.0, 0.05):
        mesh = bpy.data.meshes.new("UA_SafeLine")
        mesh.from_pydata(
            [(-w, 1.0, z), (w, 1.0, z)], [], []
        )
        lines.append(mesh)

    obj = bpy.data.objects.new("UA_SafeFrame", lines[0])
    obj.location = (0, 0, 0)
    scene.collection.objects.link(obj)
    obj.hide_render = True
    obj.hide_select = True
    coll = util.ensure_collection(context, "UA_Cameras")
    util.move_to_collection(obj, coll)
    # 第二条参考线同样入库
    mesh2 = bpy.data.objects.new("UA_SafeFrame_Bottom", lines[1])
    mesh2.hide_render = True
    mesh2.hide_select = True
    scene.collection.objects.link(mesh2)
    util.move_to_collection(mesh2, coll)


# ---------------------------------------------------------------------------
# 相机运镜（⑥）
# ---------------------------------------------------------------------------

ORBIT_PIVOT = "UA_OrbitPivot"


def _cam(context) -> bpy.types.Object:
    cam = context.scene.camera or util.find_object("UA_Camera")
    if cam is None:
        raise ValueError("场景里没有相机，请先新建买量工程")
    return cam


def camera_move(context, mode: str, seconds: float = 3.0) -> None:
    """相机运镜预设。mode: push_in / orbit / shake。

    一键语义：后设的运镜覆盖前设（清相机与枢轴的旧动画）。
    """
    scene = context.scene
    cam = _cam(context)
    cam.animation_data_clear()
    pivot = util.find_object(ORBIT_PIVOT)
    if pivot is not None:
        pivot.animation_data_clear()
        pivot.rotation_euler = (0, 0, 0)
    f = _f()
    # 从当前帧起编排（模板分镜用 frame_set 控制运镜时机）
    f0 = max(scene.frame_start, scene.frame_current)
    f1 = f0 + round(seconds * f)
    st = tuple(cam.location)

    if mode == "push_in":
        # 沿视线方向推进 15%（纯数学：不读新建相机的 stale 矩阵）
        props = scene.uastudio
        loc0, target = util.CAMERA_PRESETS.get(
            props.aspect, (tuple(cam.location), (0, 0, 0.35)))
        forward = (Vector(target) - Vector(loc0)).normalized()
        dist = max(1.0, (Vector(loc0) - Vector(target)).length)
        end = Vector(loc0) + forward * (dist * 0.15)
        cam.location = tuple(end)
        _kf(cam, "location", [st, tuple(end)], [f0, f1], interp="SINE")
    elif mode == "orbit":
        # 环绕：相机挂到中枢空物体，纯数学换父级（枢轴初始无旋转）
        pivot = util.find_object(ORBIT_PIVOT)
        if pivot is None:
            pivot = bpy.data.objects.new(ORBIT_PIVOT, None)
            pivot.empty_display_size = 0.2
            pivot.location = (0, 0, 0.5)
            context.scene.collection.objects.link(pivot)
            coll = util.ensure_collection(context, "UA_Cameras")
            util.move_to_collection(pivot, coll)
        from mathutils import Matrix

        cam.parent = pivot
        cam.matrix_parent_inverse = Matrix.Identity(4)
        # 父级无旋转时局部位置 = 世界位置 - 枢轴位置
        cam.location = (cam.location.x - pivot.location.x,
                        cam.location.y - pivot.location.y,
                        cam.location.z - pivot.location.z)
        pivot.rotation_euler.z = 0
        _kf(pivot, "rotation_euler",
            [(0, 0, 0), (0, 0, math.tau)], [f0, f1], interp="LINEAR")
    elif mode == "shake":
        # 震屏：0.4 秒高频抖动（贴卡点用）
        rng = random.Random(7)
        base = tuple(cam.location)
        frames = [f0 + i * 2 for i in range(round(0.4 * f / 2))]
        for i, fr in enumerate(frames):
            dx = rng.uniform(-0.05, 0.05)
            dy = rng.uniform(-0.05, 0.05)
            cam.location = (base[0] + dx, base[1] + dy, base[2])
            cam.keyframe_insert(data_path="location", frame=fr)
        cam.location = base
        cam.keyframe_insert(data_path="location", frame=frames[-1] + 2)
        for fc in _fcurves(cam.animation_data.action):
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"