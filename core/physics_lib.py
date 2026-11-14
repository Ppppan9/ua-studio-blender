"""⑤ 物理库 I：刚体碰撞 / 破碎 / 粒子特效。

刚体统一走 bpy.ops.rigidbody（自动处理世界创建），
破碎走 Cell Fracture 扩展（依赖管理器自动启用/安装），
粒子用传统粒子系统预设（金币喷泉/彩带/星尘/爆炸）。
"""

from __future__ import annotations

import math
import random

import bpy

from . import util, deps

# 破碎需要的前置插件 key（deps 注册表）
DEP_CELL_FRACTURE = "cell_fracture"


# ---------------------------------------------------------------------------
# 刚体
# ---------------------------------------------------------------------------


def ensure_world(scene) -> None:
    """确保刚体世界存在，且缓存帧范围对齐片长。"""
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    rw = scene.rigidbody_world
    if rw is None:
        raise RuntimeError("刚体世界创建失败")
    try:
        rw.point_cache.frame_start = scene.frame_start
        rw.point_cache.frame_end = scene.frame_end
    except AttributeError:
        pass


def _mass_by_size(obj, density: float = 500.0) -> float:
    """按包围盒体积估算质量。"""
    d = obj.dimensions
    return max(0.05, d.x * d.y * d.z * density)


def _new_force_field(context, name: str, loc) -> bpy.types.Object:
    """创建力场空物体（field 是懒创建属性，必须走 field_create）。"""
    empty = bpy.data.objects.new(name, None)
    empty.location = loc
    context.scene.collection.objects.link(empty)
    bpy.ops.object.select_all(action="DESELECT")
    empty.select_set(True)
    context.view_layer.objects.active = empty
    bpy.ops.object.forcefield_toggle()
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(empty, coll)
    return empty


def add_rigid(context, objects, rb_type: str = "ACTIVE") -> int:
    """给对象加刚体（ACTIVE=参与碰撞倒下，PASSIVE=固定碰撞体）。"""
    if not objects:
        raise ValueError("请先选中物体")
    ensure_world(context.scene)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    context.view_layer.objects.active = objects[0]
    bpy.ops.rigidbody.objects_add()  # 默认 ACTIVE
    for o in objects:
        rb = o.rigid_body
        if rb is None:
            continue
        rb.type = rb_type
        if rb_type == "ACTIVE":
            rb.mass = _mass_by_size(o)
            rb.collision_shape = "MESH" if len(o.data.vertices) > 500 else "CONVEX_HULL"
        # 买量片长内自动休眠收尾
        try:
            rb.use_sleeping = False
        except AttributeError:
            pass
    return len(objects)


def set_stage_passive(context) -> int:
    """把舞台物体自动设为固定碰撞体。"""
    stage = [
        util.find_object(n) for n in
        ("UA_Stage_Podium", "UA_Stage_Desk", "UA_Stage_Floor")
    ]
    stage = [o for o in stage if o is not None]
    if not stage:
        raise ValueError("场景里没有舞台，先新建买量工程")
    return add_rigid(context, stage, "PASSIVE")


def drop_pile(context, height: float = 3.0, stagger: bool = True) -> int:
    """掉落堆叠预设：选中物体抬到空中，舞台自动转固定碰撞体，一烘焙成片。"""
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs:
        raise ValueError("请先选中物体")
    rng = random.Random(11)
    set_stage_passive(context)
    for i, obj in enumerate(objs):
        add_rigid(context, [obj], "ACTIVE")
        lift = height + (i * 0.6 if stagger else 0)
        obj.location.z += lift
        if stagger:
            obj.rotation_euler.z += rng.uniform(-0.3, 0.3)
    return len(objs)


def impact(context, strength: float = 6.0) -> int:
    """冲击预设：给选中物体加刚体并放一个瞬时冲击力场。"""
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs:
        raise ValueError("请先选中物体")
    set_stage_passive(context)
    add_rigid(context, objs, "ACTIVE")

    # 冲击力场放在物体群前方
    cx = sum(o.location.x for o in objs) / len(objs)
    cy = sum(o.location.y for o in objs) / len(objs)
    cz = sum(o.location.z for o in objs) / len(objs)
    empty = _new_force_field(context, "UA_ImpactForce", (cx, cy - 2.5, cz))
    empty.empty_display_type = "SINGLE_ARROW"
    empty.rotation_euler.x = math.radians(-90)
    empty.field.type = 'FORCE'
    empty.field.strength = strength * 100
    empty.field.shape = 'PLANE'
    return len(objs)


# ---------------------------------------------------------------------------
# 破碎（Cell Fracture 扩展）
# ---------------------------------------------------------------------------


def _ensure_cell_fracture() -> None:
    """确保 Cell Fracture 就绪：未启用则启用，未安装则自动安装。"""
    st = deps.get_status("cell_fracture")
    if st == deps.S_READY:
        return
    if st == deps.S_DISABLED:
        ok, msg = deps.enable_dep("cell_fracture")
    else:
        ok, msg = deps.install_dep("cell_fracture")
    if not ok:
        raise RuntimeError(
            "Cell Fracture 前置插件不可用：" + msg
            + "；请在面板顶部「前置插件」里处理"
        )


def fracture(context, count: int, noise: float, explode: bool,
             explode_strength: float) -> int:
    """一键破碎：选中物体 → Cell Fracture → 碎片自动刚体（可选拆弹力场）。"""
    _ensure_cell_fracture()
    objs = [o for o in context.selected_objects if o.type == "MESH"]
    if not objs:
        raise ValueError("请请先选中要破碎的物体")
    ensure_world(context.scene)
    set_stage_passive(context)

    total = 0
    for obj in objs:
        before = set(bpy.data.objects)
        # source 默认值在 5.x 已损坏，显式用自身顶点；
        # 顶点数少于目标碎片数时用递归细分补足
        n_verts = max(1, len(obj.data.vertices))
        recursion = 1 if count > n_verts else 0
        rec_limit = max(2, min(16, count // n_verts)) if recursion else 8
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.add_fracture_cell_objects(
            source={"VERT_OWN"}, source_limit=count,
            recursion=recursion, recursion_source_limit=rec_limit,
            recursion_clamp=max(count * 2, 250),
            source_noise=noise, margin=0.001,
            use_recenter=True, use_remove_original=True,
            use_sharp_edges=True, use_island_split=True,
        )
        pieces = [o for o in bpy.data.objects if o not in before]
        for p in pieces:
            util.move_to_collection(p, util.ensure_collection(context, "UA_Objects"))
        total += len(pieces)
        if explode:
            add_explosion_force(context, pieces, explode_strength)
        add_rigid(context, pieces, "ACTIVE")
    return total


def add_explosion_force(context, pieces, strength: float) -> None:
    """给碎片群中心加爆开力场（EXPLODE 类型）。"""
    if not pieces:
        return
    cx = sum(p.location.x for p in pieces) / len(pieces)
    cy = sum(p.location.y for p in pieces) / len(pieces)
    cz = sum(p.location.z for p in pieces) / len(pieces)
    empty = _new_force_field(context, "UA_ExplodeForce", (cx, cy, cz))
    # 5.x 无 EXPLODE 场型，用负强度 FORCE（排斥）实现爆开
    empty.field.type = 'FORCE'
    empty.field.strength = -abs(strength) * 100
    empty.field.shape = 'POINT'


clear_cache_sentinel = None


def bake_all(context) -> None:
    """烘焙场景全部物理缓存。"""
    ensure_world(context.scene)
    try:
        bpy.ops.ptcache.bake_all(bake=True)
    except RuntimeError:
        raise RuntimeError("物理烘焙失败")


def clear_physics_cache(context) -> None:
    """清空全部物理缓存（重新模拟前用）。"""
    for ob in context.scene.objects:
        for mod in ob.modifiers:
            if mod.type == "FLUID" or hasattr(mod, "point_cache"):
                cache = getattr(mod, "point_cache", None)
                if cache is not None:
                    cache.frame_end = context.scene.frame_end
    try:
        bpy.ops.ptcache.free_bake_all()
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# 粒子特效（传统粒子系统预设）
# ---------------------------------------------------------------------------

FX_PRESETS = ("coins", "confetti", "stardust", "boom")


def _make_emitter(context, name: str, loc, size: float = 0.6) -> bpy.types.Object:
    """创建隐藏发射器平面。"""
    bpy.ops.mesh.primitive_plane_add(size=size, align="WORLD", location=loc)
    emitter = context.active_object
    emitter.name = name
    emitter.hide_render = True
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(emitter, coll)
    return emitter


def _instance_obj(kind: str) -> bpy.types.Object | None:
    """粒子渲染实例：金币/彩带/星尘/爆炸碎屑。"""
    if kind == "coins":
        from . import asset_lib
        coin = bpy.data.objects.get("UA_Coin")
        if coin is None:
            coin = asset_lib.add_shape(bpy.context, "coin")
        return coin
    if kind == "confetti":
        mesh = bpy.data.meshes.new("UA_ConfettiPlane")
        mesh.from_pydata(
            [(-0.06, -0.04, 0), (0.06, -0.04, 0),
             (0.06, 0.04, 0), (-0.06, 0.04, 0)],
            [], [(0, 1, 2, 3)],
        )
        obj = bpy.data.objects.new("UA_ConfettiPlane", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.hide_render = True
        return obj
    return None


def fx_particle(context, kind: str, count: int = 80,
                start_frame: int | None = None) -> bpy.types.Object:
    """创建粒子特效预设。kind: coins/confetti/stardust/boom/dust。

    start_frame 指定发射起始帧（模板分镜编排用），默认场景起点。
    dust = 氛围微尘：大面积慢速漂浮，画面质感层。
    """
    scene = context.scene
    ground = 0.22 if bpy.data.objects.get("UA_Stage_Podium") else 0.0
    if kind == "coins":
        loc = (0, 0, ground + 0.1)
        vel = 3.5
        life = round(scene.render.fps * 2.2)
    elif kind == "boom":
        loc = (0, 0, ground + 0.5)
        vel = 5.0
        life = round(scene.render.fps * 1.2)
    elif kind == "dust":
        loc = (0, 0, ground + 1.5)
        vel = 0.05
        life = round(scene.render.fps * 8.0)
    else:
        loc = (0, 0, ground + 3.0)  # confetti/stardust 从天上撒
        vel = 0.5
        life = round(scene.render.fps * 2.5)

    emitter_size = 4.5 if kind == "dust" else 0.6
    emitter = _make_emitter(context, "UA_FX_" + kind, loc, emitter_size)
    psys_mod = emitter.modifiers.new("UA_FX", "PARTICLE_SYSTEM")
    psys = psys_mod.particle_system

    settings = bpy.data.particles.new("UA_FX_" + kind)
    psys.settings = settings
    settings.count = count
    settings.lifetime = life
    f_start = scene.frame_start if start_frame is None else int(start_frame)
    settings.frame_start = f_start
    settings.frame_end = f_start + (2 if kind not in ("stardust", "dust") else 20)
    settings.physics_type = "NEWTON"
    settings.normal_factor = vel
    settings.tangent_factor = 1.5 if kind != "boom" else 4.0
    settings.brownian_factor = 3.0 if kind == "dust" else (
        1.5 if kind == "stardust" else 0.2)
    settings.drag_factor = 0.9 if kind == "dust" else (
        0.4 if kind == "confetti" else 0.1)
    settings.effector_weights.gravity = 0.05 if kind == "dust" else 1.0
    settings.use_rotations = True
    settings.rotation_mode = "VEL"
    settings.angular_velocity_mode = "VELOCITY"
    settings.angular_velocity_factor = 3.0 if kind == "confetti" else 1.0

    inst = _instance_obj(kind)
    if inst is not None:
        settings.render_type = "OBJECT"
        settings.instance_object = inst
        settings.particle_size = 1.0
        settings.size_random = 0.3
    else:
        settings.render_type = "HALO" if False else "OBJECT"
        # 无实例时退化为小方块实例
        settings.instance_object = _instance_obj("confetti")
        settings.particle_size = 0.15 if kind == "dust" else (
            0.25 if kind == "stardust" else 1.0)

    settings.material = 1 if False else 1
    return emitter