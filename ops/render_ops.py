"""⑦⑧ 渲染与结尾卡 Operator。"""

from __future__ import annotations

import bpy

from ..core import render_lib, endcard_lib


class UA_OT_render_current(bpy.types.Operator):
    """一键渲染当前场景（按输出预设出片）"""

    bl_idname = "ua.render_current"
    bl_label = "一键渲染当前片"
    bl_options = {"REGISTER"}

    still: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        wm = context.window_manager
        try:
            wm.progress_begin(0)
            wm.progress_update(10)
        except Exception:
            wm = None
        try:
            path = render_lib.render_current(context, still=self.still)
        except RuntimeError as exc:
            if wm is not None:
                try:
                    wm.progress_end()
                except Exception:
                    pass
            self.report({"ERROR"}, "渲染失败: " + str(exc))
            return {"CANCELLED"}
        if wm is not None:
            try:
                wm.progress_update(999)
                wm.progress_end()
            except Exception:
                pass
        self.report({"INFO"}, "输出到 " + path)
        return {"FINISHED"}


class UA_OT_batch_render(bpy.types.Operator):
    """批量渲染所有场景"""

    bl_idname = "ua.batch_render"
    bl_label = "批量渲染全部场景"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            n = render_lib.batch_render(context)
        except RuntimeError as exc:
            self.report({"ERROR"}, "批量渲染失败: " + str(exc))
            return {"CANCELLED"}
        timings = getattr(render_lib.batch_render, "last_timings", {})
        detail = "；".join(
            k + " " + str(round(v, 1)) + "s" for k, v in timings.items()
        )
        self.report({"INFO"}, str(n) + " 个场景已渲染完成（" + detail + "）")
        return {"FINISHED"}


class UA_OT_endcard(bpy.types.Operator):
    """一键结尾卡"""

    bl_idname = "ua.endcard"
    bl_label = "一键结尾卡"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        try:
            n = endcard_lib.make_endcard(
                context, props.endcard_template,
                props.logo_path, props.app_name, props.cta_text,
            )
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        if props.endcard_animate:
            endcard_lib.animate_endcard(context)
        self.report({"INFO"}, str(n) + " 个结尾卡元素已创建")
        return {"FINISHED"}


class UA_OT_logo_import(bpy.types.Operator):
    """导入 logo 图片（png 透明底最佳）"""

    bl_idname = "ua.logo_import"
    bl_label = "导入 logo"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.png;*.jpg;*.jpeg;*.webp")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        context.scene.uastudio.logo_path = self.filepath
        self.report({"INFO"}, "logo 已设置，点结尾卡模板按钮生成")
        return {"FINISHED"}


class UA_OT_size_matrix(bpy.types.Operator):
    """多尺寸矩阵：9:16 / 1:1 / 16:9 各渲染一条（机位自动适配）"""

    bl_idname = "ua.size_matrix"
    bl_label = "多尺寸矩阵出片"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            n = render_lib.render_size_matrix(context)
        except (RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 条尺寸已渲染完成")
        return {"FINISHED"}


class UA_OT_export_cover(bpy.types.Operator):
    """导出投放封面（当前帧 PNG，cover 命名）"""

    bl_idname = "ua.export_cover"
    bl_label = "导出封面图"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            out = render_lib.export_cover(
                context, context.scene.uastudio.cover_frame)
        except (RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "封面已输出 " + out)
        return {"FINISHED"}


classes = (
    UA_OT_render_current,
    UA_OT_batch_render,
    UA_OT_size_matrix,
    UA_OT_export_cover,
    UA_OT_endcard,
    UA_OT_logo_import,
)
