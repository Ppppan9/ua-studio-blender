"""N 面板：依赖状态条 + 分页（按工作流排列）。"""

from __future__ import annotations

import bpy

from ..core import deps, asset_lib, material_lib, template_lib, candy_render


class _UABase:
    bl_category = "买量工坊"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"


class UA_PT_deps(_UABase, bpy.types.Panel):
    """顶部常驻依赖状态条。"""

    bl_label = "前置插件"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        deps.scan()
        ready, total, worst = deps.summary()
        row = layout.row(align=True)
        row.label(text=f"依赖就绪 {ready}/{total}")
        row.separator()
        if worst != deps.S_READY:
            row.operator("ua.deps_fix_all", text="一键修复", icon="TOOL_SETTINGS")
        else:
            row.label(icon="CHECKMARK")

        for dep in deps.DEPS:
            st = deps.get_status(dep.key)
            box = layout.box()
            head = box.row(align=True)
            icon = deps.status_icon(st)
            head.label(text=dep.name, icon=icon)
            sub = head.row(align=True)
            sub.alignment = "RIGHT"
            sub.label(
                text=deps.status_text(st),
            )
            body = box.row(align=True)
            body.scale_y = 0.9
            body.label(text=f"{dep.purpose}", text_ctxt="买量工坊")
            act = body.row(align=True)
            act.alignment = "RIGHT"
            if st == deps.S_READY:
                pass
            elif st == deps.S_DISABLED:
                act.operator(
                    "ua.deps_install_one", text="启用", icon="PLUGIN"
                ).key = dep.key
            else:
                act.operator(
                    "ua.deps_install_one", text="安装", icon="DOWNARROW_HLT"
                ).key = dep.key

            if st == deps.S_UNAVAILABLE and deps.get_note(dep.key):
                box.label(text=deps.get_note(dep.key), icon="INFO")


class UA_PT_scene(_UABase, bpy.types.Panel):
    """① 工程：新建工程 + 尺寸/背景/舞台/灯光。"""

    bl_label = "① 工程"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        head = layout.row()
        head.label(text="一键广告模板", icon="SEQ_CHROMA_SCOPE")
        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True)
        for key, (label, _fn) in template_lib.TEMPLATES.items():
            grid.operator("ua.build_template", text=label).key = key

        head = layout.row()
        head.label(text="快捷变量（生成后改这里）", icon="GREASEPENCIL")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "app_name")
        col.prop(props, "cta_text")
        col.prop(props, "mat_color")
        row = col.row(align=True)
        row.operator("ua.template_refresh", icon="FILE_REFRESH")
        row.operator("ua.template_recolor", text="换主色", icon="COLOR")
        col.operator("ua.swap_model", text="导入模型替换主对象", icon="IMPORT")
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("ua.new_project", icon="NEW")

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "aspect")
        col.prop(props, "fps")
        col.prop(props, "duration")
        col.prop(props, "engine")
        col.operator("ua.apply_size", icon="RESTRICT_COLOR_ON")

        head = layout.row()
        head.label(text="背景", icon="WORLD")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "bg_mode")
        if props.bg_mode == "gradient":
            col.prop(props, "bg_top")
            col.prop(props, "bg_bottom")
        col.operator("ua.set_background", icon="FILE_REFRESH")

        head = layout.row()
        head.label(text="舞台", icon="MESH_CYLINDER")
        col = layout.column(align=True)
        col.prop(props, "stage")
        col.operator("ua.set_stage", icon="FILE_REFRESH")

        head = layout.row()
        head.label(text="灯光", icon="LIGHT")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "light_mode")
        col.prop(props, "light_strength")
        col.operator("ua.set_lighting", icon="FILE_REFRESH")


classes = (UA_PT_deps, UA_PT_scene)


class UA_PT_assets(_UABase, bpy.types.Panel):
    """② 资产：几何库 / 排列 / 导入 / 文字。"""

    bl_label = "② 资产"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True)
        for key, (label, _fn) in asset_lib.SHAPES.items():
            grid.operator("ua.add_shape", text=label).key = key

        head = layout.row()
        head.label(text="排列", icon="GRID")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "scatter_count")
        col.prop(props, "scatter_radius")
        col.operator("ua.scatter", icon="PARTICLES")
        col.prop(props, "grid_cols")
        col.prop(props, "grid_rows")
        col.prop(props, "grid_spacing")
        col.operator("ua.grid_array", icon="GRID")
        col.prop(props, "ring_count")
        col.prop(props, "ring_radius")
        col.operator("ua.ring_array", icon="MOD_PARTICLES")

        head = layout.row()
        head.label(text="导入与文字", icon="FILE_TICK")
        col = layout.column(align=True)
        col.operator("ua.import_asset", icon="IMPORT")
        col.prop(props, "text_body")
        col.operator("ua.text3d", icon="FONT_DATA")


class UA_PT_materials(_UABase, bpy.types.Panel):
    """③ 材质：一键材质库。"""

    bl_label = "③ 材质"
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "mat_color")
        layout.label(text="选中物体后点击一键赋材质", icon="INFO")

        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True)
        for key, (label, _b, _c) in material_lib.MATS.items():
            grid.operator("ua.apply_material", text=label).key = key


class UA_PT_animation(_UABase, bpy.types.Panel):
    """④ 动画：入场 / 循环 / 缓动 / 时间轴。"""

    bl_label = "④ 动画"
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        head = layout.row()
        head.label(text="入场（作用于选中，自动错帧）", icon="PLAY")
        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("ua.anim_entrance", text="弹出").mode = "pop"
        col.operator("ua.anim_entrance", text="坠落弹跳").mode = "drop"
        col.operator("ua.anim_entrance", text="滑入").mode = "slide"
        col.operator("ua.anim_entrance", text="旋转飞入").mode = "spin"
        col.prop(props, "entrance_gap")

        head = layout.row()
        head.label(text="循环", icon="LOOP_BACK")
        col = layout.column(align=True)
        col.operator("ua.anim_loop", text="上下浮动").mode = "float"
        col.operator("ua.anim_loop", text="旋转展示").mode = "spin"

        col.operator("ua.anim_loop", text="摇摆").mode = "sway"
        col.operator("ua.anim_loop", text="呼吸缩放").mode = "breath"

        head = layout.row()
        head.label(text="缓动与时间轴", icon="NLA")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("ua.anim_easing", text="回弹").mode = "overshoot"
        row.operator("ua.anim_easing", text="果冻弹").mode = "elastic"
        row = col.row(align=True)
        row.operator("ua.anim_easing", text="落地弹").mode = "bounce"
        row.operator("ua.anim_easing", text="匀速").mode = "linear"
        row = col.row(align=True)
        row.operator("ua.anim_easing", text="顺滑").mode = "smooth"
        row.operator("ua.anim_clear", text="清动画")
        row.operator("ua.anim_offset", text="平移")

        col.operator("ua.add_beat", icon="PMARKER")


class UA_PT_camera(_UABase, bpy.types.Panel):
    """⑥ 相机：运镜 / 构图安全区。"""

    bl_label = "⑥ 相机"
    bl_order = 7

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        head = layout.row()
        head.label(text="运镜", icon="CAMERA_DATA")
        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("ua.cam_move", text="推近").mode = "push_in"
        col.operator("ua.cam_move", text="环绕").mode = "orbit"
        col.operator("ua.cam_move", text="震屏(贴卡点)").mode = "shake"
        col.prop(props, "cam_seconds")

        head = layout.row()
        head.label(text="构图", icon="VIEW_CAMERA")
        col = layout.column(align=True)
        col.operator("ua.safety_frame", icon="MESH_GRID")


class UA_PT_gameplay(_UABase, bpy.types.Panel):
    """🎮 假玩法：手指 / 消除收集 / 飞分 / HUD。"""

    bl_label = "🎮 假玩法"
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        head = layout.row()
        head.label(text="手指引导", icon="CURSOR")
        col = layout.column(align=True)
        col.prop(props, "hand_scale")
        col.scale_y = 1.3
        col.operator("ua.hand_tap", text="手指点击选中物体", icon="OUTLINER_OB_ARMATURE")

        head = layout.row()
        head.label(text="游戏动作", icon="SOLO_ON")
        col = layout.column(align=True)
        col.prop(props, "fx_vanish_sec")
        col.prop(props, "fx_text_body")
        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True)
        grid.operator("ua.fx_vanish", text="收集飞入").mode = "corner"
        grid.operator("ua.fx_vanish", text="原地消除").mode = "shrink"
        col.operator("ua.fx_score", text="飞分文字 " + props.fx_text_body,
                     icon="SORTBYEXT")
        row = col.row(align=True)
        row.operator("ua.white_flash", text="白闪转场", icon="SEQ_CHROMA_SCOPE")
        row.operator("ua.bubble", text="文字气泡", icon="GREASEPENCIL")

        head = layout.row()
        head.label(text="HUD 层（跟随相机）", icon="IP")

        col = layout.column(align=True)
        col.prop(props, "hud_score_body")
        col.operator("ua.hud_score", icon="SEQ_PREVIEW")
        col.prop(props, "hud_ratio")
        col.operator("ua.hud_progress", icon="NLA")

        head = layout.row()
        head.label(text="贴纸（弹入）", icon="OUTLINER_OB_IMAGE")
        col = layout.column(align=True)
        col.prop(props, "sticker_symbol")
        col.prop(props, "sticker_palette")
        col.operator("ua.add_sticker", icon="BRUSH_DATA")


class UA_PT_physics(_UABase, bpy.types.Panel):
    """⑤ 物理：刚体 / 破碎 / 粒子（布料/软体/流体）。"""

    bl_label = "⑤ 物理"
    bl_order = 6

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        head = layout.row()
        head.label(text="刚体碰撞", icon="RIGID_BODY")
        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("ua.drop_pile", text="掉落堆叠")
        col.operator("ua.impact", text="冲击撞飞")
        col.operator("ua.rigid_passive", text="设为固定碰撞体")

        head = layout.row()
        head.label(text="破碎（Cell Fracture）", icon="MOD_EXPLODE")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "fracture_count")
        col.prop(props, "fracture_noise")
        col.prop(props, "fracture_explode")
        if props.fracture_explode:
            col.prop(props, "explode_strength")
        col.operator("ua.fracture", text="一键破碎", icon="MOD_EXPLODE")

        head = layout.row()
        head.label(text="粒子特效", icon="PARTICLES")
        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True)
        grid.operator("ua.fx_particle", text="金币喷泉").kind = "coins"
        grid.operator("ua.fx_particle", text="彩带庆祝").kind = "confetti"
        grid.operator("ua.fx_particle", text="星尘飘落").kind = "stardust"
        grid.operator("ua.fx_particle", text="爆炸碎屑").kind = "boom"
        col = layout.column(align=True)
        col.prop(props, "fx_count")

        head = layout.row()
        head.label(text="布料·软体·绳索·流体", icon="MOD_CLOTH")
        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True)
        grid.operator("ua.flag", text="旗帜飘动")
        grid.operator("ua.tablecloth", text="桌布铺开")
        grid.operator("ua.jelly", text="果冻 Q 弹")
        grid.operator("ua.rope", text="绳索摆挂")
        grid.operator("ua.cloth_selected", text="选中变布料")
        grid.operator("ua.fluid_splash", text="流体泼溅")
        col = layout.column(align=True)
        col.prop(props, "fluid_resolution")

        head = layout.row()
        head.label(text="总控", icon="FILE_REFRESH")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("ua.physics_bake", text="烘焙全部物理", icon="REC")
        row.operator("ua.physics_clear", text="清缓存")


class UA_PT_render(_UABase, bpy.types.Panel):
    """⑦ 渲染：输出预设 / 一键出片 / 矩阵 / 封面 / 批量。"""

    bl_label = "⑦ 渲染"
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "out_format")
        col.prop(props, "out_dir")
        col.prop(props, "transparent")

        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("ua.render_current", text="一键渲染当前片", icon="RENDER_ANIMATION")
        row = col.row(align=True)
        row.operator("ua.render_current", text="试渲染当前帧").still = True
        row.operator("ua.batch_render", text="批量渲染", icon="RENDERLAYERS")

        head = layout.row()
        head.label(text="画质与风格", icon="MOD_DOITH")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "quality_level")
        col.operator("ua.apply_quality", icon="MOD_SUBSURF")
        col.prop(props, "color_style")
        col.operator("ua.color_style", icon="COLOR")
        col.prop(props, "dof_fstop")
        row = col.row(align=True)
        row.operator("ua.dof_focus", text="景深聚焦选中", icon="FOCUS")
        row.operator("ua.dof_focus", text="关景深").disable = True
        row = col.row(align=True)
        row.operator("ua.motion_blur", text="开运动模糊").on = True
        row.operator("ua.motion_blur", text="关").on = False

        sub = layout.box()
        sub.label(text="实验性（本构建有崩溃风险）", icon="ERROR")
        sub.prop(props, "bloom_on")
        if props.bloom_on:
            sub.prop(props, "bloom_strength")
        sub.prop(props, "vignette_on")
        sub.operator("ua.setup_compositor", text="应用合成链(实验)",
                     icon="POSTPROCESS")

        head = layout.row()
        head.label(text="投放输出", icon="SEQUENCE")
        col = layout.column(align=True)
        col.prop(props, "cover_frame")
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("ua.size_matrix", text="多尺寸矩阵 3 画幅", icon="MOD_SOLIDIFY")
        col.operator("ua.export_cover", text="导出封面图", icon="FILE_IMAGE")

        head = layout.row()
        head.label(text="工程", icon="FILE_REFRESH")
        col = layout.column(align=True)
        col.operator("ua.cleanup_project", text="清理孤儿数据", icon="BRUSH_DATA")


class UA_PT_endcard(_UABase, bpy.types.Panel):
    """⑧ 结尾卡：logo / 模板 / CTA。"""

    bl_label = "⑧ 结尾卡"
    bl_order = 9

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(props, "endcard_template")
        col.prop(props, "app_name")
        col.prop(props, "cta_text")
        col.prop(props, "endcard_animate")
        col.operator("ua.logo_import", icon="IMAGE_DATA")
        if props.logo_path:
            col.label(text="logo: " + props.logo_path.split("/")[-1], icon="CHECKMARK")

        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("ua.endcard", text="一键生成结尾卡", icon="DOCUMENTS")


class UA_PT_shots(_UABase, bpy.types.Panel):
    """🎬 分镜与音效：段落结构 / 跳转 / 音效清单。"""

    bl_label = "🎬 分镜与音效"
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        col = layout.column(align=True)
        col.operator("ua.shot_setup", icon="SEQUENCE")

        shots = props.shots
        if len(shots) == 0:
            layout.label(text="尚无分镜，先点上方生成", icon="INFO")
        for i, item in enumerate(shots):
            row = layout.row(align=True)
            row.label(text=str(i + 1) + ". " + item.name
                      + "  [" + str(item.start) + "-" + str(item.end) + "]")
            row.operator("ua.shot_goto", text="跳转", icon="RESTRICT_COLOR_ON"
                         ).index = i

        head = layout.row()
        head.label(text="BGM 自动卡点", icon="FILE_SOUND")
        col = layout.column(align=True)
        col.prop(props, "bgm_path")
        col.prop(props, "beat_sensitivity")
        col.operator("ua.bgm_beats", icon="PMARKER")

        head = layout.row()
        head.label(text="交付", icon="PACKAGE")
        col = layout.column(align=True)
        col.operator("ua.sfx_list", text="导出音效清单", icon="FILE_SOUND")
        col.scale_y = 1.3
        col.operator("ua.delivery_package", text="一键交付包", icon="PACKAGE")


# ---------------------------------------------------------------------------
# 占位面板（保留机制，新增模块时替换）
# ---------------------------------------------------------------------------


class UA_PT_candy(_UABase, bpy.types.Panel):
    """🍬 糖果渲染：一键材质/圆角/灯光/背景/阵列/粒子。"""

    bl_label = "🍬 糖果渲染"
    bl_order = 11

    def draw(self, context):
        layout = self.layout
        props = context.scene.uastudio

        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("ua.candy_scene", text="一键糖果场景", icon="SHADERBALL")

        head = layout.row()
        head.label(text="材质", icon="SHADERBALL")
        col = layout.column(align=True)
        col.operator("ua.candy_mats", text="一键糖果材质（六色循环）", icon="COLOR")
        col.operator("ua.template_recolor", text="换主色", icon="COLOR")

        head = layout.row()
        head.label(text="几何", icon="MOD_BEVEL")
        row = layout.row(align=True)
        row.operator("ua.candy_bevel", text="批量圆角", icon="MOD_BEVEL")
        row.operator("ua.candy_auto_bevel", text="智能圆角", icon="SNAP_MIDPOINT")

        head = layout.row()
        head.label(text="环境", icon="LIGHT_SUN")
        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("ua.candy_full_setup", text="一键糖果渲染环境", icon="LIGHT")
        row = col.row(align=True)
        row.operator("ua.candy_light", text="灯光", icon="LIGHT_AREA")
        row.operator("ua.candy_backdrop", text="背景", icon="MATERIAL")
        row.operator("ua.candy_render_settings", text="参数", icon="SETTINGS")

        head = layout.row()
        head.label(text="快速布景", icon="GRID")
        row = layout.row(align=True)
        row.operator("ua.candy_rain", text="糖果雨", icon="PARTICLES")
        row.operator("ua.spline_array", text="沿曲线阵列", icon="MOD_ARRAY")



_PLACEHOLDERS = ()


def _make_placeholder_panel(slug: str, label: str, note: str):
    """动态构造占位 Panel 类。"""
    attrs = {
        "bl_label": label,
        "bl_order": 10 + _PLACEHOLDERS.index((slug, label, note)),
        "bl_options": {"DEFAULT_CLOSED"},
        "draw": lambda self, context: self.layout.label(text=note, icon="TIME"),
    }
    return type(f"UA_PT_{slug}", (_UABase, bpy.types.Panel), attrs)


for _slug, _label, _note in _PLACEHOLDERS:
    globals()[f"UA_PT_{_slug}"] = _make_placeholder_panel(_slug, _label, _note)

classes = tuple(
    [UA_PT_deps, UA_PT_scene, UA_PT_assets, UA_PT_materials,
     UA_PT_animation, UA_PT_gameplay, UA_PT_physics, UA_PT_camera,
     UA_PT_render, UA_PT_endcard, UA_PT_shots, UA_PT_candy]
    + [globals()[f"UA_PT_{s}"] for s, _, _ in _PLACEHOLDERS]
)