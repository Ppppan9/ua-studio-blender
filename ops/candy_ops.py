"""🍬 糖果渲染 Operator：一键材质/圆角/灯光/背景/阵列/粒子。"""

from __future__ import annotations

import bpy

from ..core import candy_render


class UA_OT_candy_mats(bpy.types.Operator):
    """给选中物体按序赋六色糖果材质"""

    bl_idname = "ua.candy_mats"
    bl_label = "一键糖果材质"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = candy_render.apply_candy_materials(context)
        self.report({"INFO"}, str(n) + " 个物体已赋糖果材质")
        return {"FINISHED"}


class UA_OT_candy_bevel(bpy.types.Operator):
    """批量圆角（固定宽度）"""

    bl_idname = "ua.candy_bevel"
    bl_label = "批量圆角"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = candy_render.bulk_bevel(context)
        self.report({"INFO"}, str(n) + " 个物体已加圆角")
        return {"FINISHED"}


class UA_OT_candy_auto_bevel(bpy.types.Operator):
    """智能圆角（按尺寸自动计算宽度）"""

    bl_idname = "ua.candy_auto_bevel"
    bl_label = "智能圆角"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = candy_render.auto_bevel_by_size(context)
        self.report({"INFO"}, str(n) + " 个物体已加智能圆角")
        return {"FINISHED"}


class UA_OT_candy_light(bpy.types.Operator):
    """糖果广告标志灯光（极柔大面积）"""

    bl_idname = "ua.candy_light"
    bl_label = "糖果灯光"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = candy_render.setup_candy_lighting(context)
        self.report({"INFO"}, str(n) + " 盏糖果灯已布置")
        return {"FINISHED"}


class UA_OT_candy_backdrop(bpy.types.Operator):
    """奶油色背景（穹幕+地面无缝一体）"""

    bl_idname = "ua.candy_backdrop"
    bl_label = "奶油背景"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        candy_render.setup_candy_backdrop(context)
        self.report({"INFO"}, "奶油色背景已就位")
        return {"FINISHED"}


class UA_OT_candy_render_settings(bpy.types.Operator):
    """渲染参数一键对齐（EEVEE 高采样+Standard 色彩）"""

    bl_idname = "ua.candy_render_settings"
    bl_label = "糖果渲染参数"
    bl_options = {"REGISTER"}

    def execute(self, context):
        candy_render.apply_candy_render_settings(context)
        self.report({"INFO"}, "渲染参数已对齐糖果风格")
        return {"FINISHED"}


class UA_OT_candy_full_setup(bpy.types.Operator):
    """一键糖果渲染环境（灯光+背景+渲染参数三合一）"""

    bl_idname = "ua.candy_full_setup"
    bl_label = "一键糖果渲染环境"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        candy_render.setup_candy_render(context)
        self.report({"INFO"}, "糖果渲染环境已就位")
        return {"FINISHED"}


class UA_OT_candy_rain(bpy.types.Operator):
    """糖果雨（迷你圆角方块三色坠落）"""

    bl_idname = "ua.candy_rain"
    bl_label = "糖果雨"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        candy_render.candy_rain(context, 60)
        self.report({"INFO"}, "糖果雨粒子已就位")
        return {"FINISHED"}


class UA_OT_spline_array(bpy.types.Operator):
    """沿选中曲线等距分布选中物体"""

    bl_idname = "ua.spline_array"
    bl_label = "沿样条线阵列"
    bl_options = {"REGISTER", "UNDO"}

    count: bpy.props.IntProperty(name="数量", default=8, min=2, max=50)

    def execute(self, context):
        try:
            n = candy_render.spline_array(context, self.count)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "沿曲线分布了 " + str(n) + " 个物体")
        return {"FINISHED"}


class UA_OT_candy_scene(bpy.types.Operator):
    """一键糖果场景（新工程+环境+示范方块+糖果雨）"""

    bl_idname = "ua.candy_scene"
    bl_label = "一键糖果场景"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        candy_render.quick_candy_scene(context)
        self.report({"INFO"}, "糖果场景已生成")
        return {"FINISHED"}


classes = (
    UA_OT_candy_mats,
    UA_OT_candy_bevel,
    UA_OT_candy_auto_bevel,
    UA_OT_candy_light,
    UA_OT_candy_backdrop,
    UA_OT_candy_render_settings,
    UA_OT_candy_full_setup,
    UA_OT_candy_rain,
    UA_OT_spline_array,
    UA_OT_candy_scene,
)
