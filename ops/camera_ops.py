"""⑥ 相机 Operator：运镜与安全区。"""

from __future__ import annotations

import bpy

from ..core import anim_lib


class UA_OT_cam_move(bpy.types.Operator):
    """相机运镜预设"""

    bl_idname = "ua.cam_move"
    bl_label = "相机运镜"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="运镜",
        items=[
            ("push_in", "推近", "沿视线推进 15%"),
            ("orbit", "环绕", "挂枢轴环绕一周"),
            ("shake", "震屏", "0.4 秒高频抖动"),
        ],
    )

    def execute(self, context):
        try:
            anim_lib.camera_move(
                context, self.mode, context.scene.uastudio.cam_seconds
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "运镜已加到广告相机")
        return {"FINISHED"}


class UA_OT_safety_frame(bpy.types.Operator):
    """创建构图安全区参考线（不渲染）"""

    bl_idname = "ua.safety_frame"
    bl_label = "构图安全区参考线"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        anim_lib.safety_frame(context)
        self.report({"INFO"}, "顶部UI区/底部CTA区参考线已创建")
        return {"FINISHED"}


classes = (UA_OT_cam_move, UA_OT_safety_frame)
