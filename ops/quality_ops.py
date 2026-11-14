"""✨ 画质 Operator：质量档位 / 合成链 / 色彩风格 / 景深 / 运动模糊。"""

from __future__ import annotations

import bpy

from ..core import quality_lib


class UA_OT_apply_quality(bpy.types.Operator):
    """切换渲染质量档位（草稿/标准/高质/电影）"""

    bl_idname = "ua.apply_quality"
    bl_label = "切换质量档位"
    bl_options = {"REGISTER"}

    def execute(self, context):
        engine = quality_lib.apply_quality(
            context, context.scene.uastudio.quality_level)
        self.report({"INFO"}, "质量档位已应用：" + engine)
        return {"FINISHED"}


class UA_OT_setup_compositor(bpy.types.Operator):
    """构建合成链（辉光 Bloom + 晕影，按面板开关）"""

    bl_idname = "ua.setup_compositor"
    bl_label = "应用辉光/晕影"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        quality_lib.setup_compositor(
            context, props.bloom_on, props.bloom_strength,
            props.vignette_on)
        self.report({"INFO"}, "合成链已更新")
        return {"FINISHED"}


class UA_OT_color_style(bpy.types.Operator):
    """应用色彩风格"""

    bl_idname = "ua.color_style"
    bl_label = "应用色彩风格"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        quality_lib.apply_color_style(
            context, context.scene.uastudio.color_style)
        self.report({"INFO"}, "色彩风格已应用")
        return {"FINISHED"}


class UA_OT_dof_focus(bpy.types.Operator):
    """开启景深，焦点对准选中物体"""

    bl_idname = "ua.dof_focus"
    bl_label = "景深聚焦选中物体"
    bl_options = {"REGISTER", "UNDO"}

    disable: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        try:
            if self.disable:
                quality_lib.disable_dof(context)
                self.report({"INFO"}, "景深已关闭")
                return {"FINISHED"}
            dist = quality_lib.apply_dof(
                context, context.view_layer.objects.active,
                context.scene.uastudio.dof_fstop)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "景深已开启，焦点距离 " + str(dist) + "m")
        return {"FINISHED"}


class UA_OT_motion_blur(bpy.types.Operator):
    """开关运动模糊"""

    bl_idname = "ua.motion_blur"
    bl_label = "运动模糊"
    bl_options = {"REGISTER"}

    on: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        quality_lib.toggle_motion_blur(context, self.on)
        self.report({"INFO"}, "运动模糊已" + ("开启" if self.on else "关闭"))
        return {"FINISHED"}


classes = (
    UA_OT_apply_quality,
    UA_OT_setup_compositor,
    UA_OT_color_style,
    UA_OT_dof_focus,
    UA_OT_motion_blur,
)
