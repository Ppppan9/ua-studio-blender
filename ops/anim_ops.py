"""④ 动画 Operator。"""

from __future__ import annotations

import bpy

from ..core import anim_lib


class UA_OT_anim_entrance(bpy.types.Operator):
    """给选中物体加入场动画（自动错帧）"""

    bl_idname = "ua.anim_entrance"
    bl_label = "入场动画"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=[
        ("pop", "弹出", "缩放 0 到 1 带回弹"),
        ("drop", "坠落弹跳", "从空中落到位"),
        ("slide", "滑入", "按顺序滑到位"),
        ("spin", "旋转飞入", "转着飞进来"),
    ])

    def execute(self, context):
        try:
            n = anim_lib.entrance(
                context, self.mode, context.scene.uastudio.entrance_gap)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已加入场动画")
        return {"FINISHED"}


class UA_OT_anim_loop(bpy.types.Operator):
    """给选中物体加循环动画"""

    bl_idname = "ua.anim_loop"
    bl_label = "循环动画"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=[
        ("float", "上下浮动", "缓入缓出上下漂"),
        ("spin", "旋转展示", "匀速转一圈"),
        ("sway", "摇摆", "左右轻摆"),
        ("breath", "呼吸缩放", "轻微放大缩小"),
    ])

    def execute(self, context):
        try:
            n = anim_lib.loop(context, self.mode)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已加循环动画")
        return {"FINISHED"}


class UA_OT_anim_easing(bpy.types.Operator):
    """一键替换选中物体关键帧缓动"""

    bl_idname = "ua.anim_easing"
    bl_label = "一键缓动"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=[
        ("overshoot", "回弹", "BACK 插值"),
        ("elastic", "果冻弹", "ELASTIC 插值"),
        ("bounce", "落地弹", "BOUNCE 插值"),
        ("linear", "匀速", "LINEAR 插值"),
        ("smooth", "顺滑", "BEZIER 插值"),
    ])

    def execute(self, context):
        try:
            n = anim_lib.apply_easing(context, self.mode)
        except (ValueError, KeyError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已改缓动")
        return {"FINISHED"}


class UA_OT_anim_clear(bpy.types.Operator):
    """清除选中物体全部动画"""

    bl_idname = "ua.anim_clear"
    bl_label = "清除动画"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            n = anim_lib.clear_animation(context)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已清动画")
        return {"FINISHED"}


class UA_OT_anim_offset(bpy.types.Operator):
    """选中物体关键帧整体平移"""

    bl_idname = "ua.anim_offset"
    bl_label = "平移关键帧"
    bl_options = {"REGISTER", "UNDO"}

    delta: bpy.props.IntProperty(name="偏移帧数", default=10)

    def execute(self, context):
        try:
            n = anim_lib.offset_animation(context, self.delta)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已平移")
        return {"FINISHED"}


class UA_OT_add_beat(bpy.types.Operator):
    """在当前帧加卡点标记（供震屏等对齐）"""

    bl_idname = "ua.add_beat"
    bl_label = "卡点标记"
    bl_options = {"REGISTER"}

    def execute(self, context):
        name = anim_lib.add_beat(context.scene)
        self.report({"INFO"}, "卡点 " + name + " 已加到当前帧")
        return {"FINISHED"}


classes = (
    UA_OT_anim_entrance,
    UA_OT_anim_loop,
    UA_OT_anim_easing,
    UA_OT_anim_clear,
    UA_OT_anim_offset,
    UA_OT_add_beat,
)
