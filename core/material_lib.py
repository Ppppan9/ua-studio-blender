"""③ 一键材质库：全程序化节点，零贴图依赖。

注册表结构：MATS = {key: MaterialDef(label, builder)}
builder(mat, color) 负责在给定材质上搭节点，统一 apply_to_selection 调用。
"""

from __future__ import annotations

import bpy


# ---------------------------------------------------------------------------
# 节点搭设小工具
# ---------------------------------------------------------------------------


def _clean_tree(mat) -> None:
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    return out


def _bsdf(mat):
    """新建 Principled BSDF（_clean_tree 清场后旧节点已不存在）。"""
    b = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (0, 0)
    return b


def _set(bsdf, name, value) -> None:
    """安全写 Principled 输入（不同版本输入名有差异则跳过）。"""
    try:
        bsdf.inputs[name].default_value = value
    except (KeyError, RuntimeError):
        pass


def _link(tree, a, out_sock, b, in_sock) -> None:
    tree.links.new(a.outputs[out_sock], b.inputs[in_sock])


# ---------------------------------------------------------------------------
# 材质构造器
# ---------------------------------------------------------------------------


def _build_candy(mat, color) -> None:
    """糖果塑料：亮色高光 + 清漆 + 轻次表面（质感升级）。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.22)
    _set(b, "Metallic", 0.0)
    _set(b, "Coat Weight", 0.6)
    _set(b, "Coat Roughness", 0.1)
    # 轻量次表面散射：糖果通透感
    _set(b, "Subsurface Weight", 0.12)
    _set(b, "Subsurface Radius", (0.1, 0.05, 0.03))
    _link(tree=mat.node_tree, a=b, out_sock="BSDF", b=out, in_sock="Surface")


def _build_metal(mat, color) -> None:
    """金属：全金属+中低粗糙。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.18)
    _set(b, "Metallic", 1.0)
    _set(b, "Coat Weight", 0.15)
    _link(tree=mat.node_tree, a=b, out_sock="BSDF", b=out, in_sock="Surface")


def _build_glass(mat, color) -> None:
    """玻璃水晶：透射+低粗糙。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.05)
    _set(b, "Transmission Weight", 1.0)
    _set(b, "IOR", 1.45)
    _set(b, "Coat Weight", 0.8)
    _link(tree=mat.node_tree, a=b, out_sock="BSDF", b=out, in_sock="Surface")


def _build_rubber(mat, color) -> None:
    """橡胶：高粗糙哑光。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.85)
    _set(b, "Metallic", 0.0)
    _link(tree=mat.node_tree, a=b, out_sock="BSDF", b=out, in_sock="Surface")


def _build_wood(mat, color) -> None:
    """木纹：波纹纹理沿条纹方向扰动颜色。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Roughness", 0.5)

    tree = mat.node_tree
    wave = tree.nodes.new("ShaderNodeTexWave")
    wave.location = (-400, 0)
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 2.2
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 2.0

    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-150, 0)
    ramp.color_ramp.elements[0].color = (*color, 1.0)
    dark = tuple(c * 0.55 for c in color)
    ramp.color_ramp.elements[1].color = (*dark, 1.0)

    _link(tree, wave, "Fac", ramp, "Fac")
    _link(tree, ramp, "Color", b, "Base Color")
    _link(tree, b, "BSDF", out, "Surface")


def _build_marble(mat, color) -> None:
    """大理石：噪声扭曲 + 灰白纹理。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Roughness", 0.15)

    tree = mat.node_tree
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, 0)
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Distortion"].default_value = 1.6

    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-250, 0)
    ramp.color_ramp.elements[0].color = (*color, 1.0)
    light = tuple(min(1.0, c * 0.4 + 0.55) for c in color)
    ramp.color_ramp.elements[1].color = (*light, 1.0)

    _link(tree, noise, "Fac", ramp, "Fac")
    _link(tree, ramp, "Color", b, "Base Color")
    _link(tree, b, "BSDF", out, "Surface")


def _build_emissive(mat, color) -> None:
    """自发光。"""
    out = _clean_tree(mat)
    tree = mat.node_tree
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (200, 0)
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = 3.0
    _link(tree, emit, "Emission", out, "Surface")


def _build_toon(mat, color) -> None:
    """卡通三渲二：Diffuse→ShaderToRGB→阶梯 ColorRamp→Emission。"""
    out = _clean_tree(mat)
    tree = mat.node_tree

    diff = tree.nodes.new("ShaderNodeBsdfDiffuse")
    diff.location = (-300, 0)
    diff.inputs["Color"].default_value = (*color, 1.0)

    to_rgb = tree.nodes.new("ShaderNodeShaderToColorInfo")  # Shader to RGB
    to_rgb.location = (-80, 0)

    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.location = (140, 0)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in color], 1.0)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*color, 1.0)
    # 中间档：加一个元素
    mid = ramp.color_ramp.elements.new(0.35)
    mid.color = (*[c * 0.8 for c in color], 1.0)

    emit = tree.nodes.new("ShaderNodeEmission")
    emit.location = (340, 0)
    emit.inputs["Strength"].default_value = 1.0

    _link(tree, diff, "BSDF", to_rgb, "Color")
    _link(tree, to_rgb, "Color", ramp, "Fac")
    _link(tree, ramp, "Color", emit, "Color")
    _link(tree, emit, "Emission", out, "Surface")


def _build_jelly(mat, color) -> None:
    """果冻半透明：重次表面 + 透射混合（Q 弹质感）。"""
    out = _clean_tree(mat)
    b = _bsdf(mat)
    _set(b, "Base Color", (*color, 1.0))
    _set(b, "Roughness", 0.08)
    _set(b, "Transmission Weight", 0.55)
    _set(b, "IOR", 1.33)
    _set(b, "Subsurface Weight", 0.3)
    _set(b, "Subsurface Radius", (0.25, 0.1, 0.06))
    _link(tree=mat.node_tree, a=b, out_sock="BSDF", b=out, in_sock="Surface")


# ---------------------------------------------------------------------------
# 注册表
# ---------------------------------------------------------------------------

# (label, builder, 固定色 or None(用面板色))
MATS = {
    "candy": ("糖果塑料", _build_candy, None),
    "gold": ("黄金", _build_metal, (1.0, 0.766, 0.336)),
    "silver": ("白银", _build_metal, (0.972, 0.96, 0.915)),
    "copper": ("红铜", _build_metal, (0.955, 0.637, 0.538)),
    "glass": ("玻璃水晶", _build_glass, (0.85, 0.95, 1.0)),
    "rubber": ("橡胶", _build_rubber, None),
    "wood": ("木纹", _build_wood, (0.42, 0.26, 0.12)),
    "marble": ("大理石", _build_marble, (0.85, 0.85, 0.87)),
    "emissive": ("自发光", _build_emissive, None),
    "toon": ("卡通三渲二", _build_toon, None),
    "jelly": ("果冻", _build_jelly, None),
}


def apply_to_selection(context, key: str, color) -> int:
    """给选中网格对象一键赋材质，返回处理数量。"""
    entry = MATS.get(key)
    if entry is None:
        raise ValueError(f"未知材质 {key}")
    label, builder, fixed = entry
    use_color = tuple(fixed) if fixed else tuple(color)[:3]

    mat_name = f"UA_{key}"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    builder(mat, use_color)

    count = 0
    for obj in context.selected_objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        count += 1
    return count
