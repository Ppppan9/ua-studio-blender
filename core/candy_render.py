"""🍬 糖果渲染工具包：对齐超休闲买量广告标志性感官风格。

从截图逆向拆解的精确参数：
- 材质：Roughness 0.08 / Coat 0.7 / SSS 0.12 / 高饱和色
- 灯光：大面积正面高位 Area + 高强度 Fill，影 子极淡
- 背景：奶油色 #F5E6D0 纯色
- 几何：所有棱边圆角 Bevel ~3-5% 尺寸
- 色彩：青/橙/紫/绿/蓝/粉 六色糖果配色方案
"""

from __future__ import annotations

import math

import bpy

from . import util

# ---------------------------------------------------------------------------
# 糖果配色方案（从截图提取）
# ---------------------------------------------------------------------------

CANDY_COLORS = {
    "cyan":   (0.00, 0.85, 0.75),
    "orange": (1.00, 0.42, 0.00),
    "purple": (0.75, 0.28, 0.95),
    "green":  (0.00, 0.75, 0.48),
    "blue":   (0.15, 0.50, 0.95),
    "pink":   (0.95, 0.30, 0.55),
}

CREAM_BG = (0.96, 0.90, 0.82)  # #F5E6D0 奶油色


# ---------------------------------------------------------------------------
# 糖果材质生成器（对齐截图精确参数）
# ---------------------------------------------------------------------------

_CANDY_MAT_PREFIX = "Candy_"


def make_candy_material(name: str, color: tuple[float, float, float],
                        roughness: float = 0.08,
                        coat: float = 0.7,
                        sss: float = 0.12) -> bpy.types.Material:
    """生成精确对齐截图风格的糖果材质。

    参数从超休闲买量广告截图逆向拆解：
    - 低 Roughness 高光泽
    - 高 Coat 清漆层（表面保护感）
    - 轻量 SSS（色彩深度）
    """
    mat_name = _CANDY_MAT_PREFIX + name
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    b = tree.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (100, 0)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = 0.0
    try:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    except (KeyError, RuntimeError):
        pass  # 4.x 以下无 Coat
    try:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.1, 0.05, 0.03)
    except (KeyError, RuntimeError):
        pass
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return mat


def candy_recolor_all(context, color_key: str) -> int:
    """把所有 Candy_ 前缀材质统一换成指定配色，返回影响材质数。"""
    color = CANDY_COLORS.get(color_key)
    if color is None:
        raise ValueError("未知配色 " + color_key)
    count = 0
    for mat in bpy.data.materials:
        if mat.name.startswith(_CANDY_MAT_PREFIX):
            b = next((n for n in mat.node_tree.nodes
                      if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
            if b:
                b.inputs["Base Color"].default_value = (*color, 1.0)
                count += 1
    return count


# ---------------------------------------------------------------------------
# 批量圆角（糖果几何核心：所有棱边圆润）
# ---------------------------------------------------------------------------


def bulk_bevel(context, width: float = 0.04, segments: int = 3) -> int:
    """给选中物体批量加圆角 Bevel（糖果几何核心步骤）。"""
    count = 0
    for obj in context.selected_objects:
        if obj.type != "MESH":
            continue
        # 移除旧 Bevel
        for mod in list(obj.modifiers):
            if mod.name == "Candy_Bevel":
                obj.modifiers.remove(mod)
        bev = obj.modifiers.new("Candy_Bevel", "BEVEL")
        bev.width = width
        bev.segments = segments
        bev.limit_method = "ANGLE"
        bev.harden_normals = False
        count += 1
    return count


def auto_bevel_by_size(context, segments: int = 3) -> int:
    """按物体尺寸自动计算圆角宽度（尺寸的 4%），更智能。"""
    count = 0
    for obj in context.selected_objects:
        if obj.type != "MESH":
            continue
        for mod in list(obj.modifiers):
            if mod.name == "Candy_Bevel":
                obj.modifiers.remove(mod)
        dims = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z)
        width = max(0.005, dims * 0.04)
        bev = obj.modifiers.new("Candy_Bevel", "BEVEL")
        bev.width = width
        bev.segments = segments
        bev.limit_method = "ANGLE"
        count += 1
    return count


def apply_candy_materials(context) -> int:
    """给选中物体按序赋六色糖果材质（自动循环配色）。"""
    keys = list(CANDY_COLORS)
    count = 0
    idx = 0
    for obj in context.selected_objects:
        if obj.type != "MESH":
            continue
        key = keys[idx % len(keys)]
        mat = make_candy_material(key, CANDY_COLORS[key])
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        idx += 1
        count += 1
    return count


# ---------------------------------------------------------------------------
# 糖果灯光（大面积正面高位 + 高强度 Fill）
# ---------------------------------------------------------------------------


def setup_candy_lighting(context) -> int:
    """糖果广告标志 lighting：极柔大面积光源，影子几乎不可见。"""
    scene = context.scene
    # 清旧灯
    for ob in list(scene.objects):
        if ob.type == "LIGHT" and ob.name.startswith("UA_Candy"):
            bpy.data.objects.remove(ob, do_unlink=True)

    coll = util.ensure_collection(context, "UA_Candy_Lights")

    # Key：超大 Area 从正前上方（影子极淡的关键）
    util.add_light(
        context, "UA_Candy_Key", "AREA",
        (0, -5.5, 6.0), energy=200, size=10.0,
        target=(0, 0, 0.5), coll=coll,
    )
    # Fill：左前低角度补光（消除暗面）
    util.add_light(
        context, "UA_Candy_Fill", "AREA",
        (-4.0, -3.0, 2.0), energy=100, size=6.0,
        target=(0, 0, 0.5), color=(0.95, 0.97, 1.0), coll=coll,
    )
    # Rim：右后方微弱轮廓
    util.add_light(
        context, "UA_Candy_Rim", "AREA",
        (3.0, 3.0, 3.0), energy=60, size=3.0,
        target=(0, 0, 0.5), coll=coll,
    )
    return 3


# ---------------------------------------------------------------------------
# 奶油背景（纯色地面 + 穹幕一体）
# ---------------------------------------------------------------------------


def setup_candy_backdrop(context, color=None) -> int:
    """糖果广告背景：奶油色穹幕 + 无限地面（无地面线）。"""
    scene = context.scene
    bg_color = color or CREAM_BG
    # 删掉渐变穹幕（否则覆盖奶油色世界）
    dome = util.find_object("UA_Backdrop")
    if dome is not None:
        bpy.data.objects.remove(dome, do_unlink=True)

    # 用 existing 穹幕系统但换成糖果色
    from . import endcard_lib
    _ = endcard_lib

    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("UA_Candy_World")
        scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputWorld")
    out.location = (400, 0)
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.location = (150, 0)
    bg.inputs["Color"].default_value = (*bg_color, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # 无限地面（大平面同色，与背景无缝融合）
    floor = util.find_object("UA_Candy_Floor")
    if floor is None:
        bpy.ops.mesh.primitive_plane_add(size=80, align="WORLD",
                                         location=(0, 0, 0))
        floor = context.active_object
        floor.name = "UA_Candy_Floor"
    floor_mat = bpy.data.materials.get("UA_Candy_Floor_Mat")
    if floor_mat is None:
        floor_mat = bpy.data.materials.new("UA_Candy_Floor_Mat")
    floor_mat.use_nodes = True
    ftree = floor_mat.node_tree
    ftree.nodes.clear()
    fout = ftree.nodes.new("ShaderNodeOutputMaterial")
    fout.location = (300, 0)
    fb = ftree.nodes.new("ShaderNodeBsdfPrincipled")
    fb.location = (60, 0)
    fb.inputs["Base Color"].default_value = (*bg_color, 1.0)
    fb.inputs["Roughness"].default_value = 1.0
    ftree.links.new(fb.outputs["BSDF"], fout.inputs["Surface"])
    floor.data.materials.clear()
    floor.data.materials.append(floor_mat)
    floor.visible_shadow = False
    return 1


# ---------------------------------------------------------------------------
# 渲染参数（EEVEE 一键匹配糖果质感）
# ---------------------------------------------------------------------------


def apply_candy_render_settings(context) -> None:
    """渲染参数一键对齐：EEVEE 高采样+光追+Standard 色彩+无 AgX。"""
    scene = context.scene
    from . import util
    util.apply_engine(scene, "standard")
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "None"
    except (AttributeError, TypeError):
        pass
    # 阴影柔化
    try:
        scene.eevee.shadow_step_size = 4.0
    except (AttributeError, TypeError):
        pass


def setup_candy_render(context) -> int:
    """一键糖果渲染环境：灯光 + 背景 + 渲染参数 三合一。"""
    setup_candy_lighting(context)
    setup_candy_backdrop(context)
    apply_candy_render_settings(context)
    return 1


# ---------------------------------------------------------------------------
# 糖果雨粒子（迷你圆角方块三色坠落）
# ---------------------------------------------------------------------------


def candy_rain(context, count: int = 80,
               start_frame: int | None = None) -> bpy.types.Object:
    """糖果雨：迷你圆角方块三色坠落（对齐截图底部粒子效果）。"""
    scene = context.scene
    from . import physics_lib

    f_start = scene.frame_start if start_frame is None else int(start_frame)
    emitter = physics_lib._make_emitter(
        context, "UA_FX_candy_rain", (0, 0, scene.frame_end * 0.02 + 3.5),
        size=3.5,
    )
    psys_mod = emitter.modifiers.new("UA_FX", "PARTICLE_SYSTEM")
    psys = psys_mod.particle_system
    settings = bpy.data.particles.new("UA_FX_candy_rain")
    psys.settings = settings
    settings.count = count
    settings.lifetime = round(scene.render.fps * 3.0)
    settings.frame_start = f_start
    settings.frame_end = f_start + 30
    settings.physics_type = "NEWTON"
    settings.normal_factor = 0.3
    settings.brownian_factor = 1.0
    settings.drag_factor = 0.5
    settings.effector_weights.gravity = 0.6
    settings.use_rotations = True
    settings.rotation_mode = "VEL"
    settings.angular_velocity_mode = "VELOCITY"
    settings.angular_velocity_factor = 2.0
    settings.particle_size = 0.06

    for i, key in enumerate(list(CANDY_COLORS)[:3]):
        color = CANDY_COLORS[key]
        mat = make_candy_material("mini_" + key, color, sss=0.08)
        if i == 0:
            # 第一个色做实例对象
            bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD",
                                            location=(99, 99, 99))
            mini = context.active_object
            mini.name = "UA_CandyMini"
            mini.scale = (0.05, 0.05, 0.05)
            _bev = mini.modifiers.new("Candy_Bevel", "BEVEL")
            _bev.width = 0.015
            _bev.segments = 2
            mini.data.materials.append(mat)
            mini.hide_render = True
            util.move_to_collection(
                mini, util.ensure_collection(context, "UA_Objects"))

    settings.render_type = "OBJECT"
    mini_obj = bpy.data.objects.get("UA_CandyMini")
    if mini_obj:
        settings.instance_object = mini_obj
    return emitter


# ---------------------------------------------------------------------------
# 样条线阵列（沿曲线分布物体）
# ---------------------------------------------------------------------------


def spline_array(context, count: int = 8, offset_z: float = 0.0) -> int:
    """沿选中曲线等距分布选中物体副本。"""
    curve_obj = None
    src_obj = None
    for ob in context.selected_objects:
        if ob.type == "CURVE":
            curve_obj = ob
        elif ob.type == "MESH":
            src_obj = ob
    if curve_obj is None or src_obj is None:
        raise ValueError("请同时选中一条曲线和一个源物体")

    positions = []
    if curve_obj.data.splines:
        spline = curve_obj.data.splines[0]
        if spline.type == 'BEZIER':
            pts = [curve_obj.matrix_world @ p.co
                   for p in spline.bezier_points]
        else:
            pts = [curve_obj.matrix_world @ p.co for p in spline.points]
        for i in range(count):
            t = i / max(1, count - 1)
            seg = min(int(t * (len(pts) - 1)), len(pts) - 2)
            frac = t * (len(pts) - 1) - seg
            a = pts[seg]
            b = pts[seg + 1] if seg + 1 < len(pts) else pts[-1]
            positions.append(a + (b - a) * frac)

    done = 0
    for pos in positions:
        dup = src_obj.copy()
        dup.location = pos
        bpy.context.scene.collection.objects.link(dup)
        coll = util.ensure_collection(context, "UA_Objects")
        util.move_to_collection(dup, coll)
        done += 1
    return done


# ---------------------------------------------------------------------------
# 智能网格阵列（间距自动匹配尺寸）
# ---------------------------------------------------------------------------


def smart_grid(context, cols: int = 4, rows: int = 3,
               gap: float = 0.1) -> int:
    """智能网格阵列：间距自动按源物体尺寸 + gap 计算。"""
    src_objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not src_objs:
        raise ValueError("请先选中要阵列的物体")
    from . import asset_lib

    return asset_lib.grid_array(context, cols, rows,
                                max(src_objs[0].dimensions.x + gap, 0.1))


# ---------------------------------------------------------------------------
# 一键糖果场景（新工程 → 糖果渲染环境 + 示范方块）
# ---------------------------------------------------------------------------


def quick_candy_scene(context) -> int:
    """一键糖果场景：新工程 → 糖果环境 → 三层圆角方块堆叠示范。"""
    from . import scene_lib
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "floor"
    props.light_mode = "none"  # 用糖果灯光替代
    scene_lib.new_project(context, props)
    scene = context.scene

    setup_candy_lighting(context)
    setup_candy_backdrop(context)
    apply_candy_render_settings(context)

    # 相机推近到方块充满画面
    cam = util.find_object("UA_Camera")
    if cam is not None:
        cam.location = (0.7, -3.8, 2.8)
        util.look_at(cam, (0, 0, 0.35))

    # 三层示范方块（对齐截图：青/橙/紫/绿 交替堆叠，贴地）
    keys = list(CANDY_COLORS)
    for li in range(3):
        for bi in range(2):
            key = keys[(li * 2 + bi) % len(keys)]
            color = CANDY_COLORS[key]
            mat = make_candy_material(key, color)
            x = -0.55 + bi * 1.1
            z = 0.15 + li * 0.30
            rot = math.radians(90) if li % 2 else 0
            bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD",
                                            location=(x, 0, z))
            blk = context.active_object
            blk.scale = (1.0, 0.5, 0.28)
            blk.rotation_euler = (0, 0, rot)
            blk.data.materials.clear()
            blk.data.materials.append(mat)
            bev = blk.modifiers.new("Candy_Bevel", "BEVEL")
            bev.width = 0.03
            bev.segments = 3
            util.move_to_collection(
                blk, util.ensure_collection(context, "UA_Objects"))

    candy_rain(context, 60, start_frame=60)
    return 1
