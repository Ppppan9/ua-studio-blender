"""⑤ 物理库 II：Mantaflow 流体泼溅预设。

低分辨率起步（默认 48），创建后点「烘焙全部物理」出效果；
Domain/Flow/Effector 全自动配好。
"""

from __future__ import annotations

import bpy

from . import util


def splash(context, resolution: int = 48) -> bpy.types.Object:
    """快速泼溅预设：液滴落到展台 + 展台自动变障碍物。"""
    scene = context.scene
    ground = 0.22 if bpy.data.objects.get("UA_Stage_Podium") else 0.0

    # Domain：包裹舞台中心的空间
    bpy.ops.mesh.primitive_cube_add(
        size=1, align="WORLD", location=(0, 0, ground + 1.1),
    )
    domain = context.active_object
    domain.name = "UA_FluidDomain"
    domain.scale = (2.4, 2.4, 2.2)
    domain.display_type = "WIRE"
    domain.hide_render = True
    mod = domain.modifiers.new("UA_Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "LIQUID"
    ds.resolution_max = resolution
    try:
        ds.domain_size = 2.4
    except AttributeError:
        pass
    ds.use_bubble_particles = False
    try:
        cache = ds.domain_cache
        cache.frame_start = scene.frame_start
        cache.frame_end = scene.frame_end
    except AttributeError:
        pass
    coll = util.ensure_collection(context, "UA_Objects")
    util.move_to_collection(domain, coll)

    # Flow：下落液滴
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.25, segments=32, ring_count=16,
        align="WORLD", location=(0, -0.8, ground + 1.8),
    )
    flow = context.active_object
    flow.name = "UA_FluidDrop"
    fmod = flow.modifiers.new("UA_Flow", "FLUID")
    fmod.fluid_type = "FLOW"
    fs = fmod.flow_settings
    fs.flow_type = "LIQUID"
    fs.flow_behavior = "INFLOW"
    fs.use_initial_velocity = True
    fs.velocity_factor = 1.5
    flow.hide_render = True
    util.move_to_collection(flow, coll)

    # Effector：舞台变障碍物
    for name in ("UA_Stage_Podium", "UA_Stage_Desk", "UA_Stage_Floor"):
        stage_obj = util.find_object(name)
        if stage_obj is None:
            continue
        smod = stage_obj.modifiers.get("UA_FluidEffector")
        if smod is None:
            smod = stage_obj.modifiers.new("UA_FluidEffector", "FLUID")
        smod.fluid_type = "EFFECTOR"
        smod.effector_settings.effector_type = "COLLISION"

    return domain
