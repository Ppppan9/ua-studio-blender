"""🎮 假玩法库：手指点击 / 消除飞走 / 收集飞入 / 飞分文字 / HUD 层。

这是买量"假玩法"广告的动作语言：物体被手指点按、被消除飞走、
被收集飞向分数栏，屏幕上飞出 +100，顶部有分数/进度 HUD。
全部动画用逐键赋值关键帧（anim_lib._kf），无物理依赖。
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from . import anim_lib, util

HUD_COLL = "UA_HUD"


def _cam_vectors(context) -> tuple[Vector, Vector, Vector, Vector]:
    """返回 (相机位置, 视线方向, 画面右方向, 画面上方向)。

    相机在当前 view layer 内，矩阵可信；仍用 to_3x3 而非整矩阵乘。
    """
    cam = context.scene.camera or util.find_object("UA_Camera")
    if cam is None:
        raise ValueError("场景里没有相机，请先新建买量工程")
    mat = cam.matrix_world
    fwd = (mat.to_3x3() @ Vector((0, 0, -1))).normalized()
    right = (mat.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = (mat.to_3x3() @ Vector((0, 1, 0))).normalized()
    return mat.translation.copy(), fwd, right, up


def _sel_one(context) -> bpy.types.Object:
    objs = [o for o in context.selected_objects if o.type in {"MESH", "FONT"}]
    if not objs:
        raise ValueError("请先选中目标物体")
    return objs[0]


# ---------------------------------------------------------------------------
# 手指点击
# ---------------------------------------------------------------------------

HAND_NAME = "UA_Hand"
RING_NAME = "UA_ClickRing"


def make_hand(context, hand_scale: float = 1.0) -> bpy.types.Object:
    """创建卡通手指（胶囊食指 + 圆形指尖），供「手指点击」使用。"""
    old = util.find_object(HAND_NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    loc = _sel_one(context).location.copy()
    cam_loc, fwd, right, up = _cam_vectors(context)
    # 手指从画面右侧伸入，悬停在目标上方
    hover = loc + Vector((0, 0, 1.1)) + right * 0.6

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.09, depth=0.7, vertices=32,
        align="WORLD", location=hover + Vector((0, 0, 0.35)),
    )
    body = context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.09, segments=32, ring_count=16,
        align="WORLD", location=hover + Vector((0, 0, 0.7)),
    )
    tip = context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    tip.select_set(True)
    context.view_layer.objects.active = body
    bpy.ops.object.join()
    hand = context.active_object
    hand.name = HAND_NAME
    for poly in hand.data.polygons:
        poly.use_smooth = True

    mat = bpy.data.materials.get("UA_HandSkin")
    if mat is None:
        mat = bpy.data.materials.new("UA_HandSkin")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    b = tree.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (100, 0)
    b.inputs["Base Color"].default_value = (1.0, 0.82, 0.68, 1.0)
    b.inputs["Roughness"].default_value = 0.55
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    hand.data.materials.append(mat)

    hand.scale = (hand_scale, hand_scale, hand_scale)
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(hand, coll)
    return hand


def hand_tap(context, hand_scale: float = 1.0) -> int:
    """手指点击：指尖飞到选中物体 → 按下 → 弹起，物体同步按压回弹，
    并生成一圈点击波纹。返回处理物体数。"""
    target = _sel_one(context)
    scene = context.scene
    f = anim_lib._f()
    f0 = max(scene.frame_start, scene.frame_current)
    cam_loc, fwd, right, up = _cam_vectors(context)

    hand = util.find_object(HAND_NAME) or make_hand(context, hand_scale)
    hand.animation_data_clear()

    # 指尖位置 = 目标物顶面
    top = target.location + Vector((0, 0, target.dimensions.z * 0.5 + 0.05))
    start = top + right * 1.6 + up * 0.9          # 画面右上方
    press = top + Vector((0, 0, -0.08))            # 按下时指尖下压

    # 手指路径：飞入 → 按下 → 弹起
    loc_st = tuple(hand.location)
    seq = [(start, f0 + round(0.35 * f)), (press, f0 + round(0.6 * f)),
           (top, f0 + round(0.8 * f))]
    anim_lib._kf(hand, "location",
                 [loc_st] + [tuple(p) for p, _f in seq],
                 [f0] + [fr for _p, fr in seq], interp="SINE")

    # 目标物体按压回弹（与手指按下同步）
    st = tuple(target.scale)
    k_down, k_up = f0 + round(0.6 * f), f0 + round(0.85 * f)
    target.scale = tuple(c * 0.85 for c in st)
    target.keyframe_insert(data_path="scale", frame=k_down)
    target.scale = st
    target.keyframe_insert(data_path="scale", frame=k_up)
    anim_lib._set_all_interp(target, "scale", "BACK")

    # 点击波纹：圆环扩散后缩小消失
    old = util.find_object(RING_NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.18, minor_radius=0.02,
        align="WORLD", location=top + fwd * 0.02,
    )
    ring = context.active_object
    ring.name = RING_NAME
    ring.rotation_euler = target.rotation_euler
    ring_mat = bpy.data.materials.get("UA_ClickRing")
    if ring_mat is None:
        ring_mat = bpy.data.materials.new("UA_ClickRing")
    ring_mat.use_nodes = True
    rtree = ring_mat.node_tree
    rtree.nodes.clear()
    rout = rtree.nodes.new("ShaderNodeOutputMaterial")
    rout.location = (300, 0)
    remit = rtree.nodes.new("ShaderNodeEmission")
    remit.location = (60, 0)
    remit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    remit.inputs["Strength"].default_value = 2.0
    rtree.links.new(remit.outputs["Emission"], rout.inputs["Surface"])
    ring.data.materials.append(ring_mat)
    ring.scale = (0.2, 0.2, 0.2)
    anim_lib._kf(ring, "scale",
                 [(0.2, 0.2, 0.2), (1.6, 1.6, 1.6), (0.0, 0.0, 0.0)],
                 [f0 + round(0.6 * f), f0 + round(1.0 * f),
                  f0 + round(1.4 * f)], interp="SINE")
    util.move_to_collection(ring, util.ensure_collection(context, "UA_Objects"))
    return 1


# ---------------------------------------------------------------------------
# 消除飞走 / 收集飞入 / 飞分文字
# ---------------------------------------------------------------------------


def fx_vanish(context, seconds: float, to_corner: bool) -> int:
    """消除动画：选中物体弧线飞向屏幕角（收集）或原地缩小消失。

    to_corner=True 飞向画面右上角（模拟飞入分数栏），
    False 原地缩小消失（模拟消除）。
    """
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs:
        raise ValueError("请先选中要消除的物体")
    f = anim_lib._f()
    f0 = max(context.scene.frame_start, context.scene.frame_current)
    dur = max(round(0.2 * f), round(seconds * f))
    cam_loc, fwd, right, up = _cam_vectors(context)

    for i, obj in enumerate(objs):
        st_loc = tuple(obj.location)
        st_scale = tuple(obj.scale)
        start = f0 + i * round(0.08 * f)
        # 目标点：屏幕右上角（相机前方 3m 处偏右上）
        corner = cam_loc + fwd * 3.0 + right * 1.1 + up * 0.9
        # 弧线中点：抬起 0.8m
        mid = (
            (st_loc[0] + corner.x) / 2,
            (st_loc[1] + corner.y) / 2,
            max(st_loc[2], corner.z) + 0.8,
        )
        if to_corner:
            anim_lib._kf(obj, "location",
                         [st_loc, mid, tuple(corner)],
                         [start, start + dur // 2, start + dur],
                         interp="SINE")
            anim_lib._kf(obj, "scale",
                         [st_scale, st_scale, (0.001,) * 3],
                         [start, start + dur // 2, start + dur],
                         interp="SINE")
        else:
            anim_lib._kf(obj, "scale",
                         [st_scale, tuple(c * 1.15 for c in st_scale),
                          (0.001,) * 3],
                         [start, start + dur // 3, start + dur],
                         interp="BACK")
    return len(objs)


def fx_score_text(context, body: str, seconds: float = 0.9) -> int:
    """+100 飞分：在选中物体上方弹出文字并上浮淡出（缩小消失）。"""
    target = _sel_one(context)
    scene = context.scene
    f = anim_lib._f()
    f0 = max(scene.frame_start, scene.frame_current)

    curve = bpy.data.curves.new("UA_ScoreTxt", type="FONT")
    curve.body = body
    curve.size = 0.3
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.01
    obj = bpy.data.objects.new("UA_ScoreTxt", curve)
    base_z = target.location.z + target.dimensions.z * 0.5 + 0.3
    obj.location = (target.location.x, target.location.y, base_z)
    obj.rotation_euler = scene.camera.rotation_euler if scene.camera else (0, 0, 0)
    scene.collection.objects.link(obj)

    mat = bpy.data.materials.get("UA_ScoreTxt_Mat")
    if mat is None:
        mat = bpy.data.materials.new("UA_ScoreTxt_Mat")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (60, 0)
    emit.inputs["Color"].default_value = (1.0, 0.85, 0.2, 1.0)
    emit.inputs["Strength"].default_value = 2.5
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    obj.data.materials.append(mat)

    dur = max(round(0.3 * f), round(seconds * f))
    anim_lib._kf(obj, "scale",
                 [(0.001,) * 3, (1.3, 1.3, 1.3), (1.0, 1.0, 1.0),
                  (0.001,) * 3],
                 [f0, f0 + round(0.15 * f), f0 + round(0.4 * f),
                  f0 + dur], interp="BACK")
    z0 = obj.location.z
    anim_lib._kf(obj, "location",
                 [(obj.location.x, obj.location.y, z0),
                  (obj.location.x, obj.location.y, z0 + 0.5)],
                 [f0, f0 + dur], interp="SINE")
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(obj, coll)
    return 1


# ---------------------------------------------------------------------------
# HUD 层（相机子级，跟随运镜）
# ---------------------------------------------------------------------------


def _hud_mat(name, color, strength: float = 1.0) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (60, 0)
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _hud_plane(context, name, size, local_loc, color) -> bpy.types.Object:
    """在相机前方挂一块自发光平面（相机子级，跟随运镜）。"""
    cam = context.scene.camera or util.find_object("UA_Camera")
    if cam is None:
        raise ValueError("场景里没有相机")
    mesh = bpy.data.meshes.new(name)
    w, h = size
    mesh.from_pydata(
        [(-w/2, 0, -h/2), (w/2, 0, -h/2), (w/2, 0, h/2), (-w/2, 0, h/2)],
        [], [(0, 1, 2, 3)],
    )
    obj = bpy.data.objects.new(name, mesh)
    obj.location = local_loc
    obj.data.materials.append(_hud_mat(name + "_Mat", color))
    context.scene.collection.objects.link(obj)
    obj.parent = cam
    coll = util.ensure_collection(context, HUD_COLL)
    util.move_to_collection(obj, coll)
    return obj


def _hud_text(context, body, size, local_loc, name, color) -> bpy.types.Object:
    cam = context.scene.camera or util.find_object("UA_Camera")
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.004
    obj = bpy.data.objects.new(name, curve)
    obj.location = local_loc
    obj.data.materials.append(_hud_mat(name + "_Mat", color))
    context.scene.collection.objects.link(obj)
    obj.parent = cam
    coll = util.ensure_collection(context, HUD_COLL)
    util.move_to_collection(obj, coll)
    return obj


def make_hud_score(context, body: str) -> int:
    """顶部分数栏：底板 + 金币圆点 + 分数文字。

    相机局部坐标（Z 负=前方）。1m 处 9:16 视锥约 ±0.21 宽 × ±0.36 高，
    HUD 尺寸位置按此标定。
    """
    self_clean(context, "UA_HUD_Score")
    self_clean(context, "UA_HUD_Coin")
    _hud_plane(context, "UA_HUD_ScoreBG", (0.46, 0.085), (0.0, 0.245, -1.0),
               (0.08, 0.10, 0.16))
    _hud_plane(context, "UA_HUD_Coin", (0.06, 0.06), (-0.165, 0.245, -1.0),
               (1.0, 0.78, 0.25))
    _hud_text(context, body, 0.042, (0.04, 0.245, -1.0), "UA_HUD_Score",
              (1.0, 1.0, 1.0))
    return 3


def make_hud_progress(context, ratio: float = 0.62) -> int:
    """顶部进度条：深色底条 + 绿色填充（当前比例）。"""
    self_clean(context, "UA_HUD_Bar")
    bar_z = -1.0
    _hud_plane(context, "UA_HUD_BarBG", (0.42, 0.045), (0.0, 0.185, bar_z),
               (0.10, 0.12, 0.18))
    fill = _hud_plane(context, "UA_HUD_BarFill", (0.395, 0.03),
                      (0.0, 0.1825, bar_z), (0.25, 0.85, 0.45))
    # 填充比例：把网格原点挪到左端，再 scale.x = ratio
    from mathutils import Matrix

    fill.data.transform(Matrix.Translation((0.1975, 0, 0)))
    fill.scale = (ratio, 1.0, 1.0)
    return 2


def self_clean(context, prefix: str = "UA_HUD") -> None:
    """清掉旧 HUD 元素（重建前调用，按前缀避免互删）。"""
    for ob in list(bpy.data.objects):
        if ob.name.startswith(prefix):
            bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------------------
# 工程清理
# ---------------------------------------------------------------------------


def cleanup_project() -> int:
    """清理孤儿数据（无引用网格/材质/图像等），返回清理数量。"""
    before = sum(len(d) for d in (
        bpy.data.meshes, bpy.data.materials, bpy.data.images,
        bpy.data.curves, bpy.data.lights, bpy.data.cameras,
        bpy.data.particles, bpy.data.actions,
    ))
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True,
                           do_recursive=True)
    after = sum(len(d) for d in (
        bpy.data.meshes, bpy.data.materials, bpy.data.images,
        bpy.data.curves, bpy.data.lights, bpy.data.cameras,
        bpy.data.particles, bpy.data.actions,
    ))
    return before - after


# ---------------------------------------------------------------------------
# 贴纸层（表情/符号/弹幕文案，相机子级 + 弹入动画）
# ---------------------------------------------------------------------------

STICKER_PALETTE = {
    "gold": ((1.0, 0.85, 0.25), (0.35, 0.22, 0.05)),
    "fire": ((1.0, 0.45, 0.15), (0.4, 0.08, 0.02)),
    "cool": ((0.35, 0.75, 1.0), (0.05, 0.15, 0.35)),
    "mint": ((0.4, 0.95, 0.6), (0.03, 0.25, 0.12)),
}


def add_sticker(context, symbol: str, palette: str = "gold",
                size: float = 0.16) -> int:
    """贴纸：彩色圆底板 + 符号/文案，相机子级，BACK 弹入。

    symbol 可用字体支持的符号（★ ! ✓ ? ×）或中文短语（哇！/冲刺!/666）。
    """
    cam = context.scene.camera or util.find_object("UA_Camera")
    if cam is None:
        raise ValueError("场景里没有相机")
    outer, inner = STICKER_PALETTE.get(palette, STICKER_PALETTE["gold"])
    f = anim_lib._f()
    f0 = max(context.scene.frame_start, context.scene.frame_current)

    # 位置：相机前 1.1m，右上角偏移（避开中心主体）
    loc = Vector((0.52, 0.55, -1.1))

    bpy.ops.mesh.primitive_cylinder_add(
        radius=size / 2, depth=0.01, vertices=48,
        align="WORLD", location=loc,
    )
    base = context.active_object
    base.name = "UA_Sticker_Base"
    base.data.materials.append(_hud_mat("UA_StickerBG_" + palette, outer,
                                        strength=1.2))
    # 圆柱扁平朝向在相机局部空间天然正对视线，无需旋转
    base.parent = cam
    base.location = loc

    txt = bpy.data.curves.new("UA_Sticker_Txt", type="FONT")
    txt.body = symbol
    txt.size = size * 0.9
    txt.align_x = "CENTER"
    txt.align_y = "CENTER"
    tobj = bpy.data.objects.new("UA_Sticker_Txt", txt)
    tobj.location = (loc.x, loc.y, loc.z + 0.008)
    tobj.data.materials.append(_hud_mat("UA_StickerTxt_" + palette, inner,
                                        strength=1.5))
    context.scene.collection.objects.link(tobj)
    tobj.parent = cam

    coll = util.ensure_collection(context, HUD_COLL)
    for ob in (base, tobj):
        util.move_to_collection(ob, coll)

    # 弹入动画（BACK overshoot）
    for ob in (base, tobj):
        st = tuple(ob.scale)
        k1 = f0 + 1
        k2 = k1 + round(0.3 * f)
        ob.scale = (0.001,) * 3
        ob.keyframe_insert(data_path="scale", frame=k1)
        ob.scale = st
        ob.keyframe_insert(data_path="scale", frame=k2)
        anim_lib._set_all_interp(ob, "scale", "BACK")
    return 2


# ---------------------------------------------------------------------------
# 白闪转场（分镜衔接）
# ---------------------------------------------------------------------------

FLASH_NAME = "UA_Flash"


def white_flash(context, at_frame=None, seconds: float = 0.2) -> int:
    """白闪转场：相机前白幕快速全屏闪现后消失（分镜衔接用）。

    at_frame 为 None 时从当前帧起播。返回创建对象数（1）。
    """
    scene = context.scene
    cam = scene.camera or util.find_object("UA_Camera")
    if cam is None:
        raise ValueError("场景里没有相机")
    f = anim_lib._f()
    start = (scene.frame_current if at_frame is None else int(at_frame))
    f0 = max(scene.frame_start, start)
    k1 = f0
    k2 = f0 + round(0.08 * f)      # 亮起
    k3 = f0 + round(seconds * f)   # 消失

    old = util.find_object(FLASH_NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    mesh = bpy.data.meshes.new(FLASH_NAME)
    # XY 面板（法线朝相机），挂在相机局部 -0.6m 前方
    mesh.from_pydata(
        [(-2.4, -4.2, 0), (2.4, -4.2, 0), (2.4, 4.2, 0), (-2.4, 4.2, 0)],
        [], [(0, 1, 2, 3)],
    )
    obj = bpy.data.objects.new(FLASH_NAME, mesh)
    obj.parent = cam
    obj.location = (0, 0, -0.6)
    mat = bpy.data.materials.get("UA_Flash_Mat")
    if mat is None:
        mat = bpy.data.materials.new("UA_Flash_Mat")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (60, 0)
    emit.inputs["Color"].default_value = (1, 1, 1, 1)
    emit.inputs["Strength"].default_value = 3.0
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    obj.data.materials.append(mat)
    scene.collection.objects.link(obj)

    # 缩放开合模拟闪现（emission 强度不支持逐键）
    obj.scale = (0.001, 0.001, 0.001)
    obj.keyframe_insert(data_path="scale", frame=k1)
    obj.scale = (1.0, 1.0, 1.0)
    obj.keyframe_insert(data_path="scale", frame=k2)
    obj.scale = (0.001, 0.001, 0.001)
    obj.keyframe_insert(data_path="scale", frame=k3)
    anim_lib._set_all_interp(obj, "scale", "SINE")

    coll = util.ensure_collection(context, HUD_COLL)
    util.move_to_collection(obj, coll)
    return 1


# ---------------------------------------------------------------------------
# 模板素材替换（网格交换保动画）
# ---------------------------------------------------------------------------


def _detect_main_prefix(context) -> str:
    """自动检测模板主对象前缀：找 UA_ 前缀且带动画的最大同前缀组。"""
    groups: dict[str, int] = {}
    for ob in context.scene.objects:
        if not ob.name.startswith("UA_") or ob.type != "MESH":
            continue
        # 取名字中最后一个 _ 分隔前的稳定前缀（去掉尾编号）
        parts = ob.name.rsplit("_", 1)
        prefix = parts[0] if len(parts) > 1 else ob.name
        if ob.animation_data:
            groups[prefix] = groups.get(prefix, 0) + 1
    if not groups:
        raise ValueError("未找到带动画的模板主对象")
    return max(groups, key=groups.get)


def swap_template_mesh(context, imported_obj) -> int:
    """把模板主对象的网格数据换成选中导入模型的网格。

    保留全部动画/变换/材质槽结构——只换几何体。
    导入模型的材质自动传播（共享 mesh data）。
    返回替换数量。
    """
    if imported_obj.type != "MESH":
        raise ValueError("请选中一个网格模型")
    prefix = _detect_main_prefix(context)
    count = 0
    src_mats = [m for m in imported_obj.data.materials if m]
    for ob in context.scene.objects:
        if not ob.name.startswith(prefix) or ob.type != "MESH":
            continue
        if ob.data is imported_obj.data:
            continue
        ob.data = imported_obj.data
        # 导入模型材质传播到替换体
        ob.data.materials.clear()
        for m in src_mats:
            ob.data.materials.append(m)
        count += 1
    return count
