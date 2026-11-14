"""✨ 渲染质量库：质量档位 / 合成链（Bloom+晕影）/ 色彩风格 / 景深 / 运动模糊。

买量素材的画质三件套：
- 质量档位：草稿(预览) → 标准 → 高质 → 电影(Cycles)，一键切换全套渲染参数
- 合成链：RenderLayers → Glare 辉光 → 晕影 → 输出（Bloom 是发光元素质感关键）
- 色彩风格：明快/浓郁/冷暖调，通过曝光/伽马/对比度组合
"""

from __future__ import annotations

import bpy


# ---------------------------------------------------------------------------
# 质量档位
# ---------------------------------------------------------------------------

QUALITY_LEVELS = ("draft", "standard", "high", "film")


def apply_quality(context, level: str) -> str:
    """一键切换渲染质量档位，返回实际应用的引擎 ID。

    draft    EEVEE 16 采样，关光追（预览用）
    standard EEVEE 64 采样 + 光追（日常出片）
    high     EEVEE 256 采样 + 光追（精修）
    film     Cycles 256 采样 + 降噪 + 运动模糊（封面/大片）
    """
    scene = context.scene
    from . import util

    engine = util.eevee_id()
    if level == "film":
        scene.render.engine = "CYCLES"
        cycles = scene.cycles
        cycles.samples = 256
        cycles.use_denoising = True
        scene.render.use_motion_blur = True
        try:
            cycles.motion_blur_shutter = 0.5
        except (AttributeError, TypeError):
            pass
        return "CYCLES"

    scene.render.engine = engine
    scene.render.use_motion_blur = level == "high"
    try:
        eevee = scene.eevee
        if level == "draft":
            eevee.taa_render_samples = 16
            eevee.use_raytracing = False
        elif level == "standard":
            eevee.taa_render_samples = 64
            eevee.use_raytracing = True
        else:  # high
            eevee.taa_render_samples = 256
            eevee.use_raytracing = True
    except (AttributeError, TypeError):
        pass
    return engine


# ---------------------------------------------------------------------------
# 合成链（Bloom 辉光 + 晕影）
# ---------------------------------------------------------------------------


def setup_compositor(context, bloom_on: bool, bloom_strength: float,
                     vignette_on: bool) -> None:
    """构建合成链：渲染画面 → [Glare 辉光] → [晕影] → 输出。

    5.x 用节点组（scene.compositing_node_group）；
    老版本回退 scene.use_nodes + 场景树。
    """
    scene = context.scene
    if not (bloom_on or vignette_on):
        try:
            scene.compositing_node_group = None
        except AttributeError:
            scene.use_nodes = False
        return

    if hasattr(scene, "compositing_node_group"):
        _setup_compositor_group(scene, bloom_on, bloom_strength, vignette_on)
        return
    _setup_compositor_legacy(scene, bloom_on, bloom_strength, vignette_on)


def _build_chain(tree, bloom_on, bloom_strength, vignette_on):
    """在给定节点树/组里搭链，返回 (首输入 socket, 末节点输出)。"""
    first_in = tree.nodes["Group Input"].outputs["Image"] \
        if "Group Input" in tree.nodes else None
    return first_in


def _setup_compositor_group(scene, bloom_on, bloom_strength, vignette_on):
    """5.x：合成节点组路径。"""
    ng = bpy.data.node_groups.get("UA_Compositor")
    if ng is None:
        ng = bpy.data.node_groups.new("UA_Compositor", "CompositorNodeTree")
    ng.nodes.clear()
    # 输出 socket 存在即复用（接口清空 API 各版本有差异）
    has_out = any(s.in_out == "OUTPUT" for s in ng.interface.items_tree)
    if not has_out:
        ng.interface.new_socket("Image", in_out="OUTPUT",
                                socket_type="NodeSocketColor")
    gin = ng.nodes.new("NodeGroupInput")
    gin.location = (-500, 0)
    gout = ng.nodes.new("NodeGroupOutput")
    gout.location = (500, 0)
    # 组输出 socket 名不回显到节点（版本差异），组内仅一个输出，按索引取
    current = gin.outputs[0]

    if bloom_on:
        glare = ng.nodes.new("CompositorNodeGlare")
        glare.location = (-200, 100)
        # 5.x Glare 参数全部是输入 socket（menu/数值）
        try:
            glare.inputs["Type"].default_value = "BLOOM"
            glare.inputs["Quality"].default_value = "HIGH"
            glare.inputs["Threshold"].default_value = 1.0
            glare.inputs["Size"].default_value = 7.0
            glare.inputs["Strength"].default_value = max(
                0.0, min(1.0, bloom_strength))
        except (KeyError, TypeError):
            if hasattr(glare, "glare_type"):  # 老版本回退
                glare.glare_type = "BLOOM"
                glare.quality = "HIGH"
                glare.threshold = 1.0
                glare.size = 7
        ng.links.new(current, glare.inputs["Image"])
        current = glare.outputs["Image"]

    if vignette_on:
        # 遮罩 Value → Factor（避开 5.x 合成器 value→color 转换崩溃路径）
        mask = ng.nodes.new("CompositorNodeEllipseMask")
        mask.location = (-200, -200)
        mask.width = 0.9
        mask.height = 0.75
        mix = ng.nodes.new("ShaderNodeMix")
        mix.location = (200, 0)
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.inputs["A"].default_value = (0.38, 0.40, 0.5, 1.0)
        mix.inputs["Factor"].default_value = 0.35
        # 遮罩 Value 直连 Factor（椭圆遮罩自带软边，绕开 value→color 崩溃路径）
        ng.links.new(mask.outputs["Mask"], mix.inputs["Factor"])
        ng.links.new(current, mix.inputs["B"])
        current = mix.outputs["Result"]

    ng.links.new(current, gout.inputs[0])
    scene.compositing_node_group = ng


def _setup_compositor_legacy(scene, bloom_on, bloom_strength, vignette_on):
    """4.x 老路径：场景节点树 + Composite 输出。"""
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.location = (-500, 0)
    out = tree.nodes.new("CompositorNodeComposite")
    out.location = (500, 0)
    current = rl.outputs["Image"]

    if bloom_on:
        glare = tree.nodes.new("CompositorNodeGlare")
        glare.location = (-200, 100)
        glare.glare_type = "BLOOM"
        glare.quality = "HIGH"
        glare.threshold = 1.0
        glare.size = 7
        tree.links.new(current, glare.inputs["Image"])
        current = glare.outputs["Image"]

    if vignette_on:
        mask = tree.nodes.new("CompositorNodeEllipseMask")
        mask.location = (-200, -200)
        mask.width = 0.9
        mask.height = 0.75
        mix = tree.nodes.new("ShaderNodeMix")
        mix.location = (200, 0)
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.inputs["A"].default_value = (0.38, 0.40, 0.5, 1.0)
        mix.inputs["Factor"].default_value = 0.35
        tree.links.new(mask.outputs["Mask"], mix.inputs["Factor"])
        tree.links.new(current, mix.inputs["B"])
        current = mix.outputs["Result"]

    tree.links.new(current, out.inputs["Image"])


def apply_color_style(context, style: str) -> None:
    """色彩风格：明快(bright)/浓郁(rich)/清冷(cool)/暖调(warm)。"""
    scene = context.scene
    vs = scene.view_settings
    try:
        vs.view_transform = "Standard"
    except (AttributeError, TypeError):
        pass
    # 曝光/伽马组合出风格
    presets = {
        "bright": (0.35, 0.95),   # 提亮：曝光+0.35 伽马略降
        "rich": (-0.15, 1.1),     # 浓郁：压暗+伽马提
        "cool": (0.0, 1.05),      # 清冷：中性曝光
        "warm": (0.15, 1.0),      # 暖调：轻微提亮
    }
    exposure, gamma = presets.get(style, (0.0, 1.0))
    try:
        vs.exposure = exposure
        vs.gamma = gamma
    except (AttributeError, TypeError):
        pass


# ---------------------------------------------------------------------------
# 景深
# ---------------------------------------------------------------------------


def apply_dof(context, focus_obj, fstop: float) -> str:
    """开启相机景深，焦点对准选中物体。返回焦点距离。"""
    scene = context.scene
    cam = scene.camera or util_find_cam()
    if cam is None:
        raise ValueError("场景里没有相机")
    if focus_obj is None:
        raise ValueError("请先选中聚焦目标物体")
    data = cam.data
    data.dof.use_dof = True
    data.dof.aperture_fstop = max(1.0, fstop)
    dist = (focus_obj.matrix_world.translation
            - cam.matrix_world.translation).length
    data.dof.focus_distance = max(0.1, dist)
    return round(dist, 2)


def disable_dof(context) -> None:
    cam = context.scene.camera
    if cam is not None:
        cam.data.dof.use_dof = False


def util_find_cam():
    return bpy.context.scene.camera


def toggle_motion_blur(context, on: bool) -> None:
    scene = context.scene
    scene.render.use_motion_blur = on
    if scene.render.engine == "CYCLES":
        try:
            scene.cycles.use_motion_blur = on
        except (AttributeError, TypeError):
            pass
