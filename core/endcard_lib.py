"""⑧ 结尾卡库：logo / 应用名 / 下载按钮 / CTA 模板。

模板：
- center：居中白卡片（logo + 应用名 + 按钮）
- banner：底部横条（logo + 按钮，不遮挡主体）
- splash：全屏彩底大 logo
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from . import util

APP_NAME_DEFAULT = "限时挑战"

ENDCARD_SCENE = "Scene_Endcard"


def _text(scene, body, size, location, name, color=(1.0, 1.0, 1.0)) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.008
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    # 文字默认平躺（XY 面），竖起来面向相机
    obj.rotation_euler.x = math.radians(90)
    scene.collection.objects.link(obj)
    # 自发光白字（不依赖灯光，任何背景下清晰可读）
    obj.data.materials.append(_plane_mat(name + "_Mat", color, emissive=True))
    return obj


def _plane_mat(mat_name, color, emissive: bool = False) -> bpy.types.Material:
    """纯色材质；emissive=True 用自发光（结尾卡元素不依赖灯光）。"""
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    if emissive:
        e = tree.nodes.new("ShaderNodeEmission")
        e.location = (100, 0)
        e.inputs["Color"].default_value = (*color, 1.0)
        e.inputs["Strength"].default_value = 1.0
        tree.links.new(e.outputs["Emission"], out.inputs["Surface"])
        return mat
    b = tree.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (100, 0)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.5
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _logo_plane(scene, logo_path, location, size, name) -> bpy.types.Object:
    """logo 图片平面；无图时用默认圆角块。"""
    if logo_path:
        img = bpy.data.images.load(logo_path, check_existing=True)
        mesh = bpy.data.meshes.new(name)
        w, h = size
        mesh.from_pydata(
            [(-w/2, 0, -h/2), (w/2, 0, -h/2), (w/2, 0, h/2), (-w/2, 0, h/2)],
            [], [(0, 1, 2, 3)],
        )
        obj = bpy.data.objects.new(name, mesh)
        obj.location = location
        scene.collection.objects.link(obj)
        mat = bpy.data.materials.new(name + "_Mat")
        mat.use_nodes = True
        tree = mat.node_tree
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        out = tree.nodes.get("Material Output")
        b = tree.nodes.get("Principled BSDF")
        if b is None:
            b = tree.nodes.new("ShaderNodeBsdfPrincipled")
            tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
        b.inputs["Alpha"].default_value = 1.0
        try:
            b.inputs["Transmission Weight"].default_value = 0.0
        except (KeyError, RuntimeError):
            pass
        tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        # 透明通道：贴图 Alpha → Principled Alpha
        tree.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
        obj.data.materials.append(mat)
        try:
            mat.blend_method = "BLEND"  # 4.x 旧 EEVEE
        except (AttributeError, TypeError):
            pass  # 5.x EEVEE Next 用默认混合即可
        return obj
    # 默认：圆角应用图标块
    bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD", location=location)
    icon = bpy.context.active_object
    icon.scale = (size[0], 0.06, size[1])
    icon.data.materials.append(_plane_mat("UA_EndcardIcon", (0.2, 0.45, 1.0), emissive=True))
    icon.name = name
    scene.collection.objects.link(icon)
    return icon


def _button(scene, location, name, cta) -> list:
    """下载按钮：绿色圆角块 + 文案。返回 [按钮, 文字]。"""
    bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD", location=location)
    btn = bpy.context.active_object
    btn.scale = (0.55, 0.04, 0.16)
    btn.data.materials.append(_plane_mat("UA_EndcardBtn", (0.16, 0.75, 0.35), emissive=True))
    btn.name = name
    scene.collection.objects.link(btn)
    txt = _text(scene, cta, 0.085, (location[0], location[1] + 0.03,
                                    location[2]), name + "_Text")
    txt.data.materials.append(_plane_mat("UA_EndcardBtnText", (1, 1, 1), emissive=True))
    return [btn, txt]


def make_endcard(context, template: str, logo_path: str, app_name: str,
                 cta: str) -> int:
    """一键结尾卡：创建独立场景 Scene_Endcard（正片不受影响）。

    商业逻辑：结尾卡是片尾独立镜头——独立场景让批量渲染自动输出
    「正片 + 结尾卡」两段；元素浮在程序化渐变穹幕上。
    返回创建对象数。
    """
    cam = util.find_object("UA_Camera")
    if cam is None or context.scene.camera is None:
        raise ValueError("请先新建买量工程（需要广告相机）")
    main = context.scene

    # 清旧结尾卡场景（先删其专属对象，避免孤儿 .001 污染）
    old = bpy.data.scenes.get(ENDCARD_SCENE)
    if old is not None:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.scenes.remove(old)

    # 新场景：复制渲染基础设置，片长 3 秒
    end = bpy.data.scenes.new(ENDCARD_SCENE)
    end.render.resolution_x = main.render.resolution_x
    end.render.resolution_y = main.render.resolution_y
    end.render.fps = main.render.fps
    end.render.engine = main.render.engine
    try:
        end.view_settings.view_transform = main.view_settings.view_transform
    except (AttributeError, TypeError):
        pass
    end.frame_start = 1
    end.frame_end = main.render.fps * 3

    # 元素集合
    end_coll = bpy.data.collections.new("UA_Endcard")
    end.collection.children.link(end_coll)

    # 相机（新数据，避免动正片相机）
    cam_data = bpy.data.cameras.new("UA_EndcardCam")
    cam_data.lens = 50.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0
    ecam = bpy.data.objects.new("UA_EndcardCam", cam_data)
    loc, target = util.CAMERA_PRESETS[main.uastudio.aspect]
    ecam.location = loc
    util.look_at(ecam, target)
    end_coll.objects.link(ecam)
    end.camera = ecam
    # 不读矩阵（end 场景对象不在当前 view layer，矩阵是旧的）——纯数学算朝向与基点
    face = (Vector(target) - Vector(loc)).normalized()
    base = Vector(loc) + face * 2.2

    # 穹幕：专属渐变发射材质（与主场景穹幕同配方，不影响正片配色）
    tpl_bg = {
        "center": ((0.30, 0.42, 0.72), (0.92, 0.95, 1.0)),
        "banner": ((0.02, 0.03, 0.06), (0.12, 0.13, 0.16)),
        "splash": ((0.02, 0.04, 0.14), (0.10, 0.22, 0.55)),
    }
    top_c, bottom_c = tpl_bg.get(template, tpl_bg["center"])

    dome_mat = bpy.data.materials.new("UA_EndcardBG_" + template)
    dome_mat.use_nodes = True
    dtree = dome_mat.node_tree
    dtree.nodes.clear()
    dout = dtree.nodes.new("ShaderNodeOutputMaterial")
    dout.location = (400, 0)
    demit = dtree.nodes.new("ShaderNodeEmission")
    demit.location = (150, 0)
    demit.inputs["Strength"].default_value = 1.0
    dramp = dtree.nodes.new("ShaderNodeValToRGB")
    dramp.location = (-100, 0)
    dramp.color_ramp.elements[0].position = 0.45
    dramp.color_ramp.elements[0].color = (*bottom_c, 1.0)
    dramp.color_ramp.elements[1].position = 0.8
    dramp.color_ramp.elements[1].color = (*top_c, 1.0)
    dsep = dtree.nodes.new("ShaderNodeSeparateXYZ")
    dsep.location = (-350, 0)
    dtex = dtree.nodes.new("ShaderNodeTexCoord")
    dtex.location = (-600, 0)
    dtree.links.new(dtex.outputs["Generated"], dsep.inputs["Vector"])
    dtree.links.new(dsep.outputs["Z"], dramp.inputs["Fac"])
    dtree.links.new(dramp.outputs["Color"], demit.inputs["Color"])
    dtree.links.new(demit.outputs["Emission"], dout.inputs["Surface"])

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=25, segments=64, ring_count=32, align="WORLD", location=(0, 0, 0)
    )
    dome = bpy.context.active_object
    dome.name = "UA_EndcardDome"
    dome.data.materials.clear()
    dome.data.materials.append(dome_mat)
    end_coll.objects.link(dome)
    dome.visible_diffuse = False
    dome.visible_shadow = False

    # 灯光：主光 + 补光
    from . import util as _u
    key = _u.add_light(
        context, "UA_EndcardKey", "AREA", (2.5, -4.0, 3.2),
        energy=500, size=3.0, target=(0, 0, 0.2), coll=end_coll,
    )
    fill = _u.add_light(
        context, "UA_EndcardFill", "AREA", (-4.0, -3.0, 2.0),
        energy=180, size=4.0, target=(0, 0, 0.2),
        color=(0.92, 0.95, 1.0), coll=end_coll,
    )
    # add_light 内部 move_to_collection 会换集合归属 ✓

    # 元素
    def V(x, y, z):
        return Vector((x, y, z))

    n = 0
    if template == "center":
        _logo_plane(end, logo_path, base + V(0, 0, 0.42),
                    (0.34, 0.34), "UA_EndcardLogo")
        _text(end, app_name, 0.12, base + V(0, 0, 0.02),
              "UA_CTAAppName", color=(0.15, 0.28, 0.55))
        btn, _txt = _button(end, base + V(0, 0, -0.38), "UA_EndcardBtn", cta)
        n = 4
    elif template == "banner":
        _logo_plane(end, logo_path, base + V(-0.42, 0, -0.52),
                    (0.26, 0.26), "UA_EndcardLogo")
        _text(end, app_name, 0.14,
              base + V(0.0, 0, -0.52), "UA_CTAAppName", color=(1, 1, 1))
        btn, _txt = _button(end, base + V(0.38, 0, -0.52), "UA_EndcardBtn", cta)
        n = 4
    else:  # splash
        _logo_plane(end, logo_path, base + V(0, 0, 0.34),
                    (0.62, 0.62), "UA_EndcardLogo")
        _text(end, app_name, 0.17, base + V(0, 0, -0.28), "UA_CTAAppName")
        btn, _txt = _button(end, base + V(0, 0, -0.62), "UA_EndcardBtn", cta)
        n = 4

    # 按钮 pop 入场动画（结尾卡场景帧范围 1..3s）
    from . import anim_lib
    f = end.render.fps
    st = tuple(btn.scale)
    k1 = 1 + 4 * f
    k2 = k1 + round(0.45 * f)
    btn.scale = (0.001, st[1], 0.001)
    btn.keyframe_insert(data_path="scale", frame=k1)
    btn.scale = st
    btn.keyframe_insert(data_path="scale", frame=k2)
    anim_lib._set_all_interp(btn, "scale", "BACK")

    # 切到结尾卡场景便于预览（headless 无窗口则跳过）
    try:
        context.window.scene = end
    except (AttributeError, RuntimeError):
        pass
    return n


def animate_endcard(context) -> None:
    """兼容保留：结尾卡场景创建时已带按钮入场动画。"""
    return None
