"""⑤ 物理 Operator：刚体 / 掉落 / 冲击 / 破碎 / 粒子 / 烘焙 / 布料流体。"""

from __future__ import annotations

import bpy

from ..core import physics_lib, physics_cloth, fluid_lib


class UA_OT_rigid_passive(bpy.types.Operator):
    """把选中物体设为固定碰撞体"""

    bl_idname = "ua.rigid_passive"
    bl_label = "固定碰撞体"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            n = physics_lib.add_rigid(
                context, list(context.selected_objects), "PASSIVE")
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已设为固定碰撞体")
        return {"FINISHED"}


class UA_OT_drop_pile(bpy.types.Operator):
    """掉落堆叠预设：物体上天 + 舞台自动碰撞体 + 烘焙"""

    bl_idname = "ua.drop_pile"
    bl_label = "掉落堆叠"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            n = physics_lib.drop_pile(context)
            physics_lib.bake_all(context)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已就位，物理已烘焙")
        return {"FINISHED"}


class UA_OT_impact(bpy.types.Operator):
    """冲击预设：选中物体加刚体 + 冲击力场"""

    bl_idname = "ua.impact"
    bl_label = "冲击撞飞"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            n = physics_lib.impact(
                context, context.scene.uastudio.explode_strength)
            physics_lib.bake_all(context)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已就位并烘焙")
        return {"FINISHED"}


class UA_OT_fracture(bpy.types.Operator):
    """一键破碎：选中物体 Cell Fracture + 碎片刚体"""

    bl_idname = "ua.fracture"
    bl_label = "一键破碎"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        try:
            total = physics_lib.fracture(
                context, props.fracture_count, props.fracture_noise,
                props.fracture_explode, props.explode_strength,
            )
            physics_lib.bake_all(context)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "破碎完成，共 " + str(total) + " 块碎片")
        return {"FINISHED"}


class UA_OT_fx_particle(bpy.types.Operator):
    """粒子特效预设"""

    bl_idname = "ua.fx_particle"
    bl_label = "粒子特效"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(items=[
        ("coins", "金币喷泉", "金币从展台喷出"),
        ("confetti", "彩带庆祝", "彩带从天而降"),
        ("stardust", "星尘", "闪烁星尘飘落"),
        ("boom", "爆炸碎屑", "中心爆开碎屑"),
        ("dust", "氛围微尘", "大面积慢速漂浮质感层"),
    ])

    def execute(self, context):
        props = context.scene.uastudio
        emitter = physics_lib.fx_particle(context, self.kind, props.fx_count)
        physics_lib.bake_all(context)
        self.report({"INFO"}, emitter.name + " 粒子已就绪")
        return {"FINISHED"}


class UA_OT_physics_bake(bpy.types.Operator):
    """烘焙全部物理缓存"""

    bl_idname = "ua.physics_bake"
    bl_label = "烘焙全部物理"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            physics_lib.bake_all(context)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "物理烘焙完成")
        return {"FINISHED"}


class UA_OT_physics_clear(bpy.types.Operator):
    """清空物理缓存"""

    bl_idname = "ua.physics_clear"
    bl_label = "清空物理缓存"
    bl_options = {"REGISTER"}

    def execute(self, context):
        physics_lib.clear_physics_cache(context)
        self.report({"INFO"}, "物理缓存已清空")
        return {"FINISHED"}


class UA_OT_tablecloth(bpy.types.Operator):
    """桌布预设：布料落下铺开"""

    bl_idname = "ua.tablecloth"
    bl_label = "桌布铺开"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        physics_cloth.make_tablecloth(context)
        self.report({"INFO"}, "桌布已就位，点「烘焙全部物理」看效果")
        return {"FINISHED"}


class UA_OT_jelly(bpy.types.Operator):
    """果冻预设：气压布料 Q 弹落地"""

    bl_idname = "ua.jelly"
    bl_label = "果冻 Q 弹"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        physics_cloth.make_jelly(context)
        self.report({"INFO"}, "果冻已就位，点「烘焙全部物理」看效果")
        return {"FINISHED"}


class UA_OT_rope(bpy.types.Operator):
    """绳索摆挂预设"""

    bl_idname = "ua.rope"
    bl_label = "绳索摆挂"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        physics_cloth.make_rope(context)
        self.report({"INFO"}, "绳索已就位，点「烘焙全部物理」看效果")
        return {"FINISHED"}


class UA_OT_cloth_selected(bpy.types.Operator):
    """把选中物体变成布料"""

    bl_idname = "ua.cloth_selected"
    bl_label = "选中物体变布料"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            n = physics_cloth.cloth_on_selected(context)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已变布料")
        return {"FINISHED"}


class UA_OT_fluid_splash(bpy.types.Operator):
    """流体泼溅预设（低分辨率起步）"""

    bl_idname = "ua.fluid_splash"
    bl_label = "流体泼溅"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        fluid_lib.splash(context, props.fluid_resolution)
        self.report({"INFO"}, "流体已就位（分辨率 " + str(props.fluid_resolution)
                    + "），点「烘焙全部物理」")
        return {"FINISHED"}


class UA_OT_flag(bpy.types.Operator):
    """旗帜预设：布面 + 旗杆 + 风力"""

    bl_idname = "ua.flag"
    bl_label = "旗帜飘动"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        physics_cloth.make_flag(context)
        self.report({"INFO"}, "旗帜已就位，点「烘焙全部物理」看效果")
        return {"FINISHED"}


classes = (
    UA_OT_rigid_passive,
    UA_OT_drop_pile,
    UA_OT_impact,
    UA_OT_fracture,
    UA_OT_fx_particle,
    UA_OT_physics_bake,
    UA_OT_physics_clear,
    UA_OT_tablecloth,
    UA_OT_jelly,
    UA_OT_rope,
    UA_OT_cloth_selected,
    UA_OT_fluid_splash,
    UA_OT_flag,
)
