"""通用工具：引擎/场景/集合/对象/灯光的跨模块助手。

设计约定：
- 所有「一键」功能都调用这里的小工具拼装，保证行为一致；
- 买量工程固定使用 4 个功能集合：UA_Cameras / UA_Lights / UA_Stage / UA_Objects。
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 买量工程固定功能集合，顺序即大纲顺序
UA_COLLECTIONS = ("UA_Cameras", "UA_Lights", "UA_Stage", "UA_Objects")

# 分辨率预设：key -> (宽, 高)
ASPECT_MAP = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

# 默认相机机位：key -> (位置, 注视目标)
CAMERA_PRESETS = {
    "9:16": ((0.0, -9.2, 2.4), (0.0, 0.0, 0.35)),
    "1:1": ((0.0, -9.8, 2.6), (0.0, 0.0, 0.35)),
    "16:9": ((0.0, -10.5, 2.8), (0.0, 0.0, 0.35)),
}

STAGE_MATERIAL_NAME = "UA_Stage_Base"


# ---------------------------------------------------------------------------
# 引擎与渲染基础
# ---------------------------------------------------------------------------


def eevee_id() -> str:
    """返回当前版本可用的 EEVEE 引擎 ID。

    Blender 4.2~4.x 曾用 BLENDER_EEVEE_NEXT，5.0 起回归 BLENDER_EEVEE。
    """
    engines = {
        i.identifier
        for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    }
    if "BLENDER_EEVEE" in engines:
        return "BLENDER_EEVEE"
    return "BLENDER_EEVEE_NEXT"


def apply_engine(scene: bpy.types.Scene, key: str) -> None:
    """按预设键切换渲染引擎并写好采样/降噪参数。key: 'eevee' | 'cycles'。"""
    if key == "cycles":
        scene.render.engine = "CYCLES"
        cycles = scene.cycles
        cycles.samples = 128
        cycles.preview_samples = 32
        cycles.use_denoising = True
    else:
        scene.render.engine = eevee_id()
        try:
            eevee = scene.eevee
            eevee.taa_render_samples = 64
            # EEVEE Next 才有光线追踪开关；老版本忽略
            eevee.use_raytracing = True
        except AttributeError:
            pass
    # 买量素材要高饱和鲜艳：Standard 视图变换（AgX 会把亮色压灰）
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
    except (AttributeError, TypeError):
        pass


def set_resolution(scene: bpy.types.Scene, aspect_key: str) -> tuple[int, int]:
    """按比例预设设置分辨率，返回 (宽, 高)。"""
    w, h = ASPECT_MAP[aspect_key]
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    return w, h


def set_fps(scene: bpy.types.Scene, fps: int) -> None:
    scene.render.fps = fps


def set_duration(scene: bpy.types.Scene, seconds: float) -> None:
    """按片长秒数写帧范围，起始帧固定为 1。"""
    fps = max(1, scene.render.fps)
    scene.frame_start = 1
    scene.frame_end = max(fps, round(fps * seconds))


# ---------------------------------------------------------------------------
# 场景清理
# ---------------------------------------------------------------------------


def purge_scene(context: bpy.types.Context) -> None:
    """清空当前场景全部对象与孤儿数据（保留 Blender 基础设置）。"""
    scene = context.scene
    # 允许选择隐藏对象，保证删得干净
    for ob in list(scene.objects):
        ob.hide_select = False
        ob.hide_viewport = False
        ob.hide_render = False

    bpy.ops.object.select_all(action="SELECT")
    if scene.objects:
        bpy.ops.object.delete(use_global=False)

    # 无引用的网格/材质/集合/world 一并清除
    try:
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    except RuntimeError:
        pass

    # scene.world 置空后其数据块也会被 purge
    if scene.world is not None:
        scene.world = None
        try:
            bpy.data.orphans_purge(do_recursive=True)
        except RuntimeError:
            pass


# ---------------------------------------------------------------------------
# 集合与对象
# ---------------------------------------------------------------------------


def ensure_collection(context: bpy.types.Context, name: str) -> bpy.types.Collection:
    """取回（或创建）场景根级功能集合。"""
    scene = context.scene
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if name not in {c.name for c in scene.collection.children}:
        scene.collection.children.link(coll)
    return coll


def ensure_ua_collections(context: bpy.types.Context) -> dict[str, bpy.types.Collection]:
    """确保 4 个功能集合齐备，返回 {name: Collection}。"""
    return {name: ensure_collection(context, name) for name in UA_COLLECTIONS}


def move_to_collection(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    """把对象唯一归属到目标集合（先移出其他集合）。"""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def clear_collection_objects(coll: bpy.types.Collection) -> None:
    """删除集合内全部对象（含数据清理）。"""
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    try:
        bpy.data.orphans_purge(do_recursive=True)
    except RuntimeError:
        pass


def find_object(name: str) -> bpy.types.Object | None:
    return bpy.data.objects.get(name)


def select_only(context: bpy.types.Context, objects: list[bpy.types.Object]) -> None:
    """唯一选中传入对象并把第一个设为 active。"""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.hide_select = False
        ob.select_set(True)
    if objects:
        context.view_layer.objects.active = objects[0]


# ---------------------------------------------------------------------------
# 灯光与相机
# ---------------------------------------------------------------------------


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    """让对象 -Z 轴指向目标点（灯光/相机通用）。"""
    direction = Vector(target) - obj.location
    if direction.length < 1e-6:
        return
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_light(
    context: bpy.types.Context,
    name: str,
    light_type: str,
    location: tuple[float, float, float],
    energy: float,
    target: tuple[float, float, float] | None = None,
    size: float = 1.0,
    size_y: float | None = None,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    coll: bpy.types.Collection | None = None,
) -> bpy.types.Object:
    """创建并返回一个灯光对象。type: 'AREA' | 'SUN' | 'POINT'。"""
    light_data = bpy.data.lights.new(name=name, type=light_type)
    light_data.energy = energy
    light_data.color = color
    if light_type == "AREA":
        light_data.shape = "SQUARE" if size_y is None else "RECTANGLE"
        light_data.size = size
        if size_y is not None:
            light_data.size_y = size_y

    obj = bpy.data.objects.new(name=name, object_data=light_data)
    obj.location = location
    if target is not None:
        look_at(obj, target)
    if coll is None:
        context.scene.collection.objects.link(obj)
    else:
        move_to_collection(obj, coll)
        # 保证灯光集合在渲染中可见
        coll.hide_render = False
        coll.hide_viewport = False
    return obj


def add_camera(
    context: bpy.types.Context,
    aspect_key: str,
    name: str = "UA_Camera",
    coll: bpy.types.Collection | None = None,
) -> bpy.types.Object:
    """创建买量广告相机并设为场景相机。"""
    cam_data = bpy.data.cameras.new(name=name)
    cam_data.lens = 50.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0

    obj = bpy.data.objects.new(name=name, object_data=cam_data)
    loc, target = CAMERA_PRESETS[aspect_key]
    obj.location = loc
    look_at(obj, target)
    if coll is None:
        context.scene.collection.objects.link(obj)
    else:
        move_to_collection(obj, coll)
    context.scene.camera = obj
    return obj


# ---------------------------------------------------------------------------
# 基础材质
# ---------------------------------------------------------------------------


def get_or_make_stage_material() -> bpy.types.Material:
    """舞台/地面通用中性灰材质（M2 材质库可整体替换）。"""
    mat = bpy.data.materials.get(STAGE_MATERIAL_NAME)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(STAGE_MATERIAL_NAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.42, 0.42, 0.45, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
        bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    """覆盖式赋材质（单槽）。"""
    if not obj.data or not hasattr(obj.data, "materials"):
        return
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ---------------------------------------------------------------------------
# 世界背景
# ---------------------------------------------------------------------------


def make_world_gradient(
    scene: bpy.types.Scene,
    top_color: tuple[float, float, float],
    bottom_color: tuple[float, float, float],
    span: float = 0.9,
) -> bpy.types.World:
    """构建「上深下浅」的世界渐变背景（程序化节点，零贴图）。

    注意：世界着色器的 Object 坐标是「射线方向向量」，z ∈ [-1, 1]，
    与距离无关。span 控制方向 z 的映射半程（0.9 ≈ ±64° 仰角走完整渐变）。
    """
    world = bpy.data.worlds.get("UA_World")
    if world is None:
        world = bpy.data.worlds.new("UA_World")
    scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    out = tree.nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.location = (360, 0)
    bg.inputs["Strength"].default_value = 1.0

    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.location = (120, 0)
    # Z 越高 fac 越大（红/蓝对照实验确认），elements[1] = 顶部色
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*bottom_color, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*top_color, 1.0)

    map_range = tree.nodes.new("ShaderNodeMapRange")
    map_range.location = (-160, 0)
    map_range.inputs["From Min"].default_value = -span
    map_range.inputs["From Max"].default_value = span
    map_range.clamp = True

    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-400, 0)

    tex_coord = tree.nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-640, 0)
    # 参考空物体：世界原点，保证渐变以场地中心为基准
    ref = find_object("UA_GradRef")
    if ref is None:
        ref = bpy.data.objects.new("UA_GradRef", None)
        ref.empty_display_size = 0.01
        ref.hide_render = True
        scene.collection.objects.link(ref)
    tex_coord.object = ref

    tree.links.new(tex_coord.outputs["Object"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], map_range.inputs["Value"])
    tree.links.new(map_range.outputs["Result"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


def make_world_flat(
    scene: bpy.types.Scene,
    color: tuple[float, float, float],
    strength: float = 1.0,
) -> bpy.types.World:
    """纯色世界背景。"""
    world = make_world_gradient(scene, color, color)
    # 纯色：直接把 Background 接 ramp 前色即可（渐变两端同色等价，但这里更直白）
    tree = world.node_tree
    bg = tree.nodes.get("Background")
    ramp = tree.nodes.get("ColorRamp")
    if bg and ramp:
        # 断开 ramp，改为直接取底色
        for link in list(tree.links):
            if link.to_node == bg and link.to_socket.name == "Color":
                tree.links.remove(link)
        bg.inputs["Color"].default_value = (*color, 1.0)
        bg.inputs["Strength"].default_value = strength
    return world


def make_world_sky(scene: bpy.types.Scene, strength: float = 1.0) -> bpy.types.World:
    """程序化天空（Nishita 多次散射），用于「天空光」布光模式。"""
    world = bpy.data.worlds.get("UA_World")
    if world is None:
        world = bpy.data.worlds.new("UA_World")
    scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    out = tree.nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.location = (360, 0)
    bg.inputs["Strength"].default_value = strength

    sky = tree.nodes.new("ShaderNodeTexSky")
    sky.location = (60, 0)
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except TypeError:
        sky.sky_type = "PREETHAM"
    sky.sun_elevation = math.radians(52)
    sky.sun_rotation = math.radians(155)
    sky.sun_intensity = 0.6

    tree.links.new(sky.outputs["Color"], bg.inputs["Color"])
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world


# ---------------------------------------------------------------------------
# 影棚穹幕（cyclorama）
# ---------------------------------------------------------------------------

BACKDROP_NAME = "UA_Backdrop"


def make_backdrop(
    scene: bpy.types.Scene,
    top_color: tuple[float, float, float],
    bottom_color: tuple[float, float, float],
    radius: float = 25.0,
) -> bpy.types.Object:
    """创建反扣大球壳穹幕：发射材质渐变，行为在 EEVEE/Cycles 完全确定。

    - 渐变用网格 Generated 坐标（Z 0..1），确定性远高于世界着色器坐标；
    - Emission 不受灯光影响，保证背景色纯净；
    - visible_diffuse=False：穹幕不为场景贡献环境光，灯光权威不变。
    """
    coll = ensure_collection(bpy.context, "UA_Backdrop")
    old = bpy.data.objects.get(BACKDROP_NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, segments=64, ring_count=32,
        align="WORLD", location=(0, 0, 0),
    )
    obj = bpy.context.active_object
    obj.name = BACKDROP_NAME
    if hasattr(obj.data, "polygons"):
        for poly in obj.data.polygons:
            poly.use_smooth = True

    mat = bpy.data.materials.get("UA_Backdrop_Gradient")
    if mat is None:
        mat = bpy.data.materials.new("UA_Backdrop_Gradient")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (260, 0)
    emit.inputs["Strength"].default_value = 1.0

    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.location = (0, 0)
    # 相机通常只看到穹幕中带（generated z 约 0.45~0.8），
    # 把渐变端点压进可视带，画面上下对比才明显
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (*bottom_color, 1.0)
    ramp.color_ramp.elements[1].position = 0.8
    ramp.color_ramp.elements[1].color = (*top_color, 1.0)

    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-260, 0)
    tex = tree.nodes.new("ShaderNodeTexCoord")
    tex.location = (-500, 0)

    tree.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.visible_diffuse = False
    obj.visible_shadow = False
    move_to_collection(obj, coll)
    _ = scene
    return obj


def remove_backdrop() -> None:
    """删除穹幕（切换到纯色/天空模式时用）。"""
    old = bpy.data.objects.get(BACKDROP_NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
