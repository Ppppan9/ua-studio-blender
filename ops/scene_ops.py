"""① 工程 Operator：新建工程 / 尺寸 / 背景 / 舞台 / 灯光。"""

from __future__ import annotations

import bpy

from ..core import scene_lib


class UA_OT_new_project(bpy.types.Operator):
    """一键新建买量工程：清空场景并搭好画幅/背景/舞台/灯光/相机"""

    bl_idname = "ua.new_project"
    bl_label = "新建买量工程"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_lib.new_project(context, context.scene.uastudio)
        self.report({"INFO"}, "买量工程已就绪")
        return {"FINISHED"}


class UA_OT_apply_size(bpy.types.Operator):
    """应用画幅/帧率/片长设置"""

    bl_idname = "ua.apply_size"
    bl_label = "应用尺寸/片长"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_lib.apply_size(context, context.scene.uastudio)
        sc = context.scene
        self.report({"INFO"}, "尺寸/片长已应用")
        return {"FINISHED"}


class UA_OT_set_background(bpy.types.Operator):
    """按当前设置重建背景"""

    bl_idname = "ua.set_background"
    bl_label = "重建背景"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_lib.set_background(context, context.scene.uastudio)
        self.report({"INFO"}, "背景已更新")
        return {"FINISHED"}


class UA_OT_set_stage(bpy.types.Operator):
    """按当前设置重建舞台"""

    bl_idname = "ua.set_stage"
    bl_label = "重建舞台"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_lib.set_stage(context, context.scene.uastudio)
        self.report({"INFO"}, "舞台已重建")
        return {"FINISHED"}


class UA_OT_set_lighting(bpy.types.Operator):
    """按当前设置重建灯光"""

    bl_idname = "ua.set_lighting"
    bl_label = "重建灯光"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene_lib.set_lighting(context, context.scene.uastudio)
        self.report({"INFO"}, "灯光已重建")
        return {"FINISHED"}


classes = (
    UA_OT_new_project,
    UA_OT_apply_size,
    UA_OT_set_background,
    UA_OT_set_stage,
    UA_OT_set_lighting,
)
