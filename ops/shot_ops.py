"""🎬 分镜 / 模板 / 贴纸 Operator。"""

from __future__ import annotations

import bpy

from ..core import shot_lib, template_lib, game_fx_lib, endcard_lib, beat_detect, deliver_lib, material_lib


class UA_OT_shot_setup(bpy.types.Operator):
    """生成默认分镜结构（Hook/玩法/爽点/收尾）"""

    bl_idname = "ua.shot_setup"
    bl_label = "生成默认分镜"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = shot_lib.setup_default(context)
        self.report({"INFO"}, str(n) + " 个分镜已生成")
        return {"FINISHED"}


class UA_OT_shot_goto(bpy.types.Operator):
    """跳转到分镜（渲染区间设为该分镜）"""

    bl_idname = "ua.shot_goto"
    bl_label = "跳转分镜"
    bl_options = {"REGISTER"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        try:
            start, end = shot_lib.goto_shot(context, self.index)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "已跳转 [" + str(start) + "-" + str(end) + "]")
        return {"FINISHED"}


class UA_OT_sfx_list(bpy.types.Operator):
    """导出音效需求清单 TXT（按分镜与卡点）"""

    bl_idname = "ua.sfx_list"
    bl_label = "导出音效清单"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            path = shot_lib.export_sfx_list(
                context, context.scene.uastudio.out_dir)
        except (ValueError, OSError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "音效清单已输出 " + path)
        return {"FINISHED"}


class UA_OT_build_template(bpy.types.Operator):
    """一键生成完整广告模板工程"""

    bl_idname = "ua.build_template"
    bl_label = "一键广告模板"
    bl_options = {"REGISTER", "UNDO"}

    key: bpy.props.EnumProperty(items=[
        ("drop", "掉落消除", "金币掉落+点击+收集+彩带，圆形展台"),
        ("screw", "螺丝拧拧", "桌面螺丝逐个拧出+进度条，影棚风"),
        ("level", "我要通关", "宝石矩阵点亮+三连爽点，全屏大图结尾"),
        ("doors", "数字门逃生", "数学题两扇门选对通关，flat 红蓝门"),
        ("sort", "颜色排序", "四色杯逐个点击收集，banner 结尾"),
        ("jenga", "叠叠乐倒塌", "抽块倒塌物理惊险感，center 结尾"),
    ])

    def execute(self, context):
        try:
            template_lib.build_template(context, self.key)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "模板已生成，所有元素皆可修改")
        return {"FINISHED"}


class UA_OT_add_sticker(bpy.types.Operator):
    """添加贴纸（相机前弹入）"""

    bl_idname = "ua.add_sticker"
    bl_label = "添加贴纸"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        try:
            game_fx_lib.add_sticker(
                context, props.sticker_symbol, props.sticker_palette)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "贴纸已添加并弹入")
        return {"FINISHED"}


class UA_OT_template_refresh(bpy.types.Operator):
    """应用最新文案/配色并重建结尾卡（改 props 后一键刷新）"""

    bl_idname = "ua.template_refresh"
    bl_label = "应用文案并刷新结尾卡"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        try:
            endcard_lib.make_endcard(
                context, props.endcard_template,
                props.logo_path, props.app_name, props.cta_text,
            )
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "已按最新文案重建结尾卡")
        return {"FINISHED"}


class UA_OT_bgm_beats(bpy.types.Operator):
    """导入 BGM 自动检测节拍生成卡点标记"""

    bl_idname = "ua.bgm_beats"
    bl_label = "BGM 自动卡点"
    bl_options = {"REGISTER"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.mp3;*.wav;*.m4a;*.aac;*.ogg;*.flac")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            n = beat_detect.auto_beats_from_audio(
                context, self.filepath,
                context.scene.uastudio.beat_sensitivity)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "已生成 " + str(n) + " 个卡点标记")
        return {"FINISHED"}


class UA_OT_template_recolor(bpy.types.Operator):
    """按主色重赋模板糖果材质（全部引用同步更新）"""

    bl_idname = "ua.template_recolor"
    bl_label = "按主色重赋彩色材质"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # 主色统一读主场景设置（活动场景可能停在结尾卡）
        main = next((s for s in bpy.data.scenes
                     if s.name != endcard_lib.ENDCARD_SCENE), context.scene)
        props = main.uastudio
        mat = bpy.data.materials.get("UA_candy")
        if mat is None:
            self.report({"ERROR"}, "场景里没有糖果材质（先用③材质页赋一次）")
            return {"CANCELLED"}
        material_lib.MATS["candy"][1](mat, tuple(props.mat_color)[:3])
        self.report({"INFO"}, "全部糖果材质已更新为主色")
        return {"FINISHED"}


class UA_OT_delivery_package(bpy.types.Operator):
    """一键交付包：渲染全部场景+封面+音效清单+工程副本 → zip"""

    bl_idname = "ua.delivery_package"
    bl_label = "一键交付包"
    bl_options = {"REGISTER"}

    def execute(self, context):
        wm = context.window_manager
        try:
            wm.progress_begin(0)
            wm.progress_update(10)
        except Exception:
            wm = None
        try:
            path = deliver_lib.export_delivery_package(context)
        except (RuntimeError, ValueError, OSError) as exc:
            if wm is not None:
                try:
                    wm.progress_end()
                except Exception:
                    pass
            self.report({"ERROR"}, "交付失败: " + str(exc))
            return {"CANCELLED"}
        if wm is not None:
            try:
                wm.progress_update(999)
                wm.progress_end()
            except Exception:
                pass
        self.report({"INFO"}, "交付包已输出 " + path)
        return {"FINISHED"}


class UA_OT_swap_model(bpy.types.Operator):
    """用选中模型替换模板主对象几何（保留动画/位置）"""

    bl_idname = "ua.swap_model"
    bl_label = "替换模板主对象"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        mesh_obj = None
        for ob in context.selected_objects:
            if ob.type == "MESH":
                mesh_obj = ob
                break
        if mesh_obj is None:
            for ob in context.selected_objects:
                for child in ob.children_recursive:
                    if child.type == "MESH":
                        mesh_obj = child
                        break
                if mesh_obj:
                    break
        if mesh_obj is None:
            self.report({"ERROR"}, "选中对象里没有网格")
            return {"CANCELLED"}
        try:
            n = game_fx_lib.swap_template_mesh(context, mesh_obj)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, str(n) + " 个模板对象已替换")
        return {"FINISHED"}


classes = (
    UA_OT_shot_setup,
    UA_OT_shot_goto,
    UA_OT_sfx_list,
    UA_OT_build_template,
    UA_OT_add_sticker,
    UA_OT_template_refresh,
    UA_OT_bgm_beats,
    UA_OT_template_recolor,
    UA_OT_delivery_package,
    UA_OT_swap_model,
)
