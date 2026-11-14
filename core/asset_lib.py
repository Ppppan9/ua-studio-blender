"""② 资产库：买量常用几何 / 排列 / 导入归一化 / 3D 文字。

所有几何落到 UA_Objects 集合，默认摆在舞台中心地面上。
"""

from __future__ import annotations

import math
import random

import bpy

from . import util

# 舞台顶面高度（与 scene_lib 舞台几何保持一致）
_STAGE_TOP = {
    "UA_Stage_Podium": 0.22,
    "UA_Stage_Desk": 0.70,
}


def _ground_z() -> float:
    """按现有舞台返回摆放高度。"""
    for name, z in _STAGE_TOP.items():
        if bpy.data.objects.get(name) is not None:
            return z
    return 0.0


def _finish(obj, name: str) -> bpy.types.Object:
    """统一收尾：命名/集合/落位。"""
    obj.name = name
    coll = util.ensure_collection(bpy.context, "UA_Objects")
    util.move_to_collection(obj, coll)
    return obj


def _smooth(obj) -> None:
    if hasattr(obj.data, "polygons"):
        for poly in obj.data.polygons:
            poly.use_smooth = True


def _add_bevel(obj, width: float = 0.04, segments: int = 2) -> None:
    bevel = obj.modifiers.new("UA_Bevel", "BEVEL")
    bevel.width = width
    bevel.segments = segments
    bevel.limit_method = "ANGLE"


def _spawn_location() -> tuple[float, float, float]:
    return (0.0, 0.0, _ground_z())


# ---------------------------------------------------------------------------
# 基础几何
# ---------------------------------------------------------------------------


def add_rounded_cube(context) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=0.8, align="WORLD", location=_spawn_location())
    obj = context.active_object
    _add_bevel(obj, 0.08)
    _smooth(obj)
    return _finish(obj, "UA_Cube")


def add_ball(context) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.45, segments=48, ring_count=24,
        align="WORLD", location=_spawn_location(),
    )
    obj = context.active_object
    _smooth(obj)
    return _finish(obj, "UA_Ball")


def add_gem(context) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=0.5, subdivisions=2, align="WORLD", location=_spawn_location(),
    )
    obj = context.active_object
    obj.scale = (1.0, 1.0, 0.72)
    return _finish(obj, "UA_Gem")  # 平直着色更显钻石切割感


def add_coin(context) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.45, depth=0.07, vertices=64,
        align="WORLD", location=_spawn_location(),
    )
    obj = context.active_object
    obj.rotation_euler.x = math.radians(90)
    obj.location.z = _ground_z() + 0.45
    _smooth(obj)
    return _finish(obj, "UA_Coin")


def add_capsule(context) -> bpy.types.Object:
    """胶囊：圆柱 + 两端球（5.x 无 primitive_capsule_add）。"""
    loc = _spawn_location()
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.3, depth=0.5, vertices=48, align="WORLD",
        location=(loc[0], loc[1], loc[2] + 0.25),
    )
    body = context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3, segments=48, ring_count=24, align="WORLD",
        location=(loc[0], loc[1], loc[2] + 0.5),
    )
    top = context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.3, segments=48, ring_count=24, align="WORLD",
        location=(loc[0], loc[1], loc[2]),
    )
    bottom = context.active_object
    obj = _join_parts(context, [top, body, bottom], "UA_Capsule")
    _smooth(obj)
    return obj


def add_star(context) -> bpy.types.Object:
    """五角星：2D 星形轮廓挤出。"""
    verts = []
    for i in range(10):
        a = math.pi / 2 + math.pi * i / 5
        r = 0.5 if i % 2 == 0 else 0.22
        verts.append((r * math.cos(a), r * math.sin(a), -0.05))
        verts.append((r * math.cos(a), r * math.sin(a), 0.05))
    # 上下两组顶点：偶数索引为底环、奇数为顶环
    bottom = list(range(0, 20, 2))
    top = list(range(1, 20, 2))
    faces = []
    for i in range(10):
        j = (i + 1) % 10
        faces.append((bottom[i], bottom[j], top[j], top[i]))
    faces.append(tuple(bottom))
    faces.append(tuple(top))
    mesh = bpy.data.meshes.new("UA_Star")
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new("UA_Star", mesh)
    obj.location = _spawn_location()
    bpy.context.scene.collection.objects.link(obj)
    return _finish(obj, "UA_Star")


# ---------------------------------------------------------------------------
# 复合几何（多部件 join）
# ---------------------------------------------------------------------------


def _join_parts(context, parts, name) -> bpy.types.Object:
    """把部件对象 join 成一个并返回。"""
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = context.active_object
    return _finish(obj, name)


def add_dice(context) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(
        size=0.42, align="WORLD", location=_spawn_location()
    )
    obj = context.active_object
    _add_bevel(obj, 0.06, 3)
    _smooth(obj)
    return _finish(obj, "UA_Dice")


def add_screw(context) -> bpy.types.Object:
    """螺丝钉：圆柱头 + 锥形杆，横躺展示。"""
    loc = _spawn_location()
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.16, depth=0.1, vertices=32, align="WORLD",
        location=(loc[0], loc[1], loc[2] + 0.16),
    )
    head = context.active_object
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.11, radius2=0.02, depth=0.5, vertices=32,
        align="WORLD", location=(loc[0], loc[1], loc[2] + 0.6),
    )
    shaft = context.active_object
    obj = _join_parts(context, [shaft, head], "UA_Screw")
    obj.rotation_euler.y = math.radians(90)
    obj.location.z = loc[2] + 0.16
    _smooth(obj)
    return obj


def add_puzzle(context) -> bpy.types.Object:
    """拼图块：圆角方块 + 圆柱凸点（布尔差挖一个凹槽）。"""
    loc = _spawn_location()
    bpy.ops.mesh.primitive_cube_add(
        size=0.6, align="WORLD", location=loc,
    )
    base = context.active_object
    _add_bevel(base, 0.05, 3)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.12, depth=0.12, vertices=32, align="WORLD",
        location=(loc[0] + 0.30, loc[1], loc[2] + 0.06),
    )
    knob = context.active_object

    # 凹槽：另一侧减去圆柱
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.12, depth=0.14, vertices=32, align="WORLD",
        location=(loc[0] - 0.30, loc[1], loc[2] + 0.06),
    )
    hole = context.active_object

    base.select_set(True)
    knob.select_set(True)
    context.view_layer.objects.active = base
    bool_mod = base.modifiers.new("UA_Bool", "BOOLEAN")
    bool_mod.operation = "DIFFERENCE"
    bool_mod.object = hole
    knob.select_set(False)
    hole.select_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    base.select_set(True)
    context.view_layer.objects.active = base
    bpy.ops.object.modifier_apply(modifier="UA_Bool")
    bpy.data.objects.remove(hole, do_unlink=True)

    knob.select_set(True)
    context.view_layer.objects.active = knob
    obj = _join_parts(context, [base, knob], "UA_Puzzle")
    _smooth(obj)
    return obj


def add_crate(context) -> bpy.types.Object:
    """木箱：大方块重倒角。"""
    bpy.ops.mesh.primitive_cube_add(
        size=0.7, align="WORLD", location=_spawn_location()
    )
    obj = context.active_object
    _add_bevel(obj, 0.12, 3)
    _smooth(obj)
    return _finish(obj, "UA_Crate")


def add_candy(context) -> bpy.types.Object:
    """糖果：压扁球体。"""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.4, segments=48, ring_count=24,
        align="WORLD", location=_spawn_location(),
    )
    obj = context.active_object
    obj.scale = (1.25, 0.9, 0.75)
    _smooth(obj)
    return _finish(obj, "UA_Candy")


def add_bomb(context) -> bpy.types.Object:
    """炸弹：球体 + 引信锥。"""
    loc = _spawn_location()
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.38, segments=48, ring_count=24,
        align="WORLD", location=(loc[0], loc[1], loc[2] + 0.38),
    )
    body = context.active_object
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06, depth=0.22, vertices=16, align="WORLD",
        location=(loc[0], loc[1], loc[2] + 0.85),
    )
    fuse = context.active_object
    obj = _join_parts(context, [fuse, body], "UA_Bomb")
    _smooth(obj)
    return obj


# ---------------------------------------------------------------------------
# 几何注册表
# ---------------------------------------------------------------------------

SHAPES = {
    "cube": ("圆角方块", add_rounded_cube),
    "ball": ("球体", add_ball),
    "gem": ("宝石", add_gem),
    "coin": ("金币", add_coin),
    "capsule": ("胶囊", add_capsule),
    "star": ("星星", add_star),
    "dice": ("骰子", add_dice),
    "screw": ("螺丝钉", add_screw),
    "puzzle": ("拼图块", add_puzzle),
    "crate": ("木箱", add_crate),
    "candy": ("糖果", add_candy),
    "bomb": ("炸弹", add_bomb),
}


def add_shape(context, key: str) -> bpy.types.Object:
    entry = SHAPES.get(key)
    if entry is None:
        raise ValueError(f"未知几何 {key}")
    return entry[1](context)


# ---------------------------------------------------------------------------
# 排列
# ---------------------------------------------------------------------------


def _dup(obj) -> bpy.types.Object:
    dup = obj.copy()
    bpy.context.scene.collection.objects.link(dup)
    coll = util.ensure_collection(bpy.context, "UA_Objects")
    util.move_to_collection(dup, coll)
    return dup


def scatter(context, count: int, radius: float, seed: int) -> int:
    """把选中对象随机散布 count 份在圆盘范围内，落地摆放。"""
    src = [o for o in context.selected_objects if o.type == "MESH"]
    if not src:
        raise ValueError("请先选中要散布的物体")
    rng = random.Random(seed)
    ground = _ground_z()
    n = 0
    for obj in src:
        for _ in range(count):
            dup = _dup(obj)
            a = rng.uniform(0, math.tau)
            r = radius * math.sqrt(rng.random())
            dup.location = (r * math.cos(a), r * math.sin(a), ground)
            dup.rotation_euler.z = rng.uniform(0, math.tau)
            n += 1
    return n


def grid_array(context, cols: int, rows: int, spacing: float) -> int:
    """选中对象网格阵列。"""
    src = [o for o in context.selected_objects if o.type == "MESH"]
    if not src:
        raise ValueError("请先选中要阵列的物体")
    ground = _ground_z()
    base_x = -(cols - 1) * spacing / 2
    base_y = -(rows - 1) * spacing / 2
    n = 0
    for obj in src:
        for i in range(cols):
            for j in range(rows):
                if i == 0 and j == 0:
                    continue
                dup = _dup(obj)
                dup.location = (base_x + i * spacing, base_y + j * spacing, ground)
                n += 1
    return n


def ring_array(context, count: int, radius: float) -> int:
    """选中对象环形阵列。"""
    src = [o for o in context.selected_objects if o.type == "MESH"]
    if not src:
        raise ValueError("请先选中要阵列的物体")
    ground = _ground_z()
    n = 0
    for obj in src:
        for i in range(count):
            a = math.tau * i / count
            dup = _dup(obj)
            dup.location = (
                radius * math.cos(a), radius * math.sin(a), ground,
            )
            dup.rotation_euler.z = a
            n += 1
    return n


# ---------------------------------------------------------------------------
# 导入归一化
# ---------------------------------------------------------------------------

_IMPORTERS = (
    (".fbx", "import_scene.fbx"),
    (".obj", "wm.obj_import"),
    (".glb", "import_scene.gltf"),
    (".gltf", "import_scene.gltf"),
)


def import_normalize(context, filepath: str, target_size: float = 1.5) -> list:
    """导入模型并归一化：缩放到目标尺寸、落到地面、进 UA_Objects。"""
    lower = filepath.lower()
    op_id = None
    for ext, op in _IMPORTERS:
        if lower.endswith(ext):
            op_id = op
            break
    if op_id is None:
        raise ValueError("仅支持 FBX / OBJ / GLB / glTF")

    before = set(bpy.data.objects)
    if op_id == "import_scene.fbx":
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif op_id == "wm.obj_import":
        bpy.ops.wm.obj_import(filepath=filepath)
    else:
        bpy.ops.import_scene.gltf(filepath=filepath)

    imported = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in imported if o.type == "MESH"]
    if not meshes:
        raise ValueError("导入内容里没有网格对象")

    # 归一化：包围盒最大边 → target_size，重心底部落到舞台面
    from mathutils import Vector

    min_v = Vector((1e9,) * 3)
    max_v = Vector((-1e9,) * 3)
    for o in meshes:
        for corner in o.bound_box:
            world = o.matrix_world @ Vector(corner)
            min_v = Vector(map(min, min_v, world))
            max_v = Vector(map(max, min_v, world))
    size = max((max_v - min_v).length, 1e-6)
    scale = target_size / size
    center = (min_v + max_v) / 2

    roots = [o for o in meshes if o.parent is None or o.parent not in meshes]
    for o in roots:
        o.scale = [c * scale for c in o.scale]
        o.location.x -= center.x * scale
        o.location.y -= center.y * scale
        o.location.z -= (min_v.z) * scale

    for o in imported:
        coll = util.ensure_collection(context, "UA_Objects")
        util.move_to_collection(o, coll)
    return imported


def add_text3d(context, body: str, size: float, extrude: float) -> bpy.types.Object:
    """3D 标题文字：居中、挤出、倒角。"""
    curve = bpy.data.curves.new("UA_Text_Curve", type="FONT")
    curve.body = body
    curve.size = size
    curve.extrude = extrude
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.bevel_depth = 0.008
    curve.bevel_resolution = 2
    obj = bpy.data.objects.new("UA_Text", curve)
    obj.location = (0, 0, _ground_z() + size * 0.75)
    bpy.context.scene.collection.objects.link(obj)
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(obj, coll)
    return obj
