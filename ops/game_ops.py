"""🎮 假玩法 Operator：手指点击 / 消除 / 收集 / 飞分 / HUD / 清理。"""

from __future__ import annotations

import bpy

from ..core import game_fx_lib


class UA_OT_hand_tap(bpy.types.Operator):
    """手指点击选中物体（自动飞入+按压+波纹，物体同步回弹）"""

    bl_idname = "ua.hand_tap"
    bl_label = "手指点击"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            game_fx_lib.hand_tap(
                context, context.scene.uastudio.hand_scale)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "手指点击动画已生成（当前帧起播放）")
        return {"FINISHED"}


class UA_OT_fx_vanish(bpy.types.Operator):
    """消除/收集动画"""

    bl_idname = "ua.fx_vanish"
    bl_label = "消除/收集"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=[
        ("corner", "收集飞入", "弧线飞向画面右上角"),
        ("shrink", "原地消除", "放大一下再缩小消失"),
    ])

    def execute(self, context):
        try:
            n = game_fx_lib.fx_vanish(
                context, context.scene.uastudio.fx_vanish_sec,
                to_corner=(self.mode == "corner"),
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个物体已加消除动画")
        return {"FINISHED"}


class UA_OT_fx_score(bpy.types.Operator):
    """+100 飞分文字（在选中物体上方弹出上浮）"""

    bl_idname = "ua.fx_score"
    bl_label = "飞分文字"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            game_fx_lib.fx_score_text(
                context, context.scene.uastudio.fx_text_body)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "飞分文字已生成")
        return {"FINISHED"}


class UA_OT_hud_score(bpy.types.Operator):
    """顶部分数栏 HUD（跟随相机）"""

    bl_idname = "ua.hud_score"
    bl_label = "分数栏"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            game_fx_lib.make_hud_score(
                context, context.scene.uastudio.hud_score_body)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "分数栏已挂到相机前")
        return {"FINISHED"}


class UA_OT_hud_progress(bpy.types.Operator):
    """顶部进度条 HUD（跟随相机）"""

    bl_idname = "ua.hud_progress"
    bl_label = "进度条"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            game_fx_lib.make_hud_progress(
                context, context.scene.uastudio.hud_ratio)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "进度条已挂到相机前")
        return {"FINISHED"}


class UA_OT_cleanup_project(bpy.types.Operator):
    """清理工程孤儿数据（无引用网格/材质/图像等）"""

    bl_idname = "ua.cleanup_project"
    bl_label = "清理工程"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = game_fx_lib.cleanup_project()
        self.report({"INFO"}, "已清理 " + str(n) + " 个孤儿数据块")
        return {"FINISHED"}


class UA_OT_white_flash(bpy.types.Operator):
    """白闪转场（当前帧起快速闪现）"""

    bl_idname = "ua.white_flash"
    bl_label = "白闪转场"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            game_fx_lib.white_flash(context)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "白闪转场已加到当前帧")
        return {"FINISHED"}


class UA_OT_bubble(bpy.types.Operator):
    """文字气泡（中上方弹出，改文案后可重复加）"""

    bl_idname = "ua.bubble"
    bl_label = "文字气泡"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        try:
            game_fx_lib.add_sticker(
                context, props.fx_text_body or "哇！", "mint", size=0.2)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "气泡已弹出")
        return {"FINISHED"}


classes = (
    UA_OT_hand_tap,
    UA_OT_fx_vanish,
    UA_OT_fx_score,
    UA_OT_hud_score,
    UA_OT_hud_progress,
    UA_OT_white_flash,
    UA_OT_bubble,
    UA_OT_cleanup_project,
)
