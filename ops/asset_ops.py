"""② 资产 Operator：几何 / 排列 / 导入 / 文字。"""

from __future__ import annotations

import bpy

from ..core import asset_lib


class UA_OT_add_shape(bpy.types.Operator):
    """添加买量常用几何（自动落到舞台面）"""

    bl_idname = "ua.add_shape"
    bl_label = "添加几何"
    bl_options = {"REGISTER", "UNDO"}

    key: bpy.props.StringProperty()

    def execute(self, context):
        asset_lib.add_shape(context, self.key)
        self.report({"INFO"}, f"已添加 {asset_lib.SHAPES[self.key][0]}")
        return {"FINISHED"}


class UA_OT_scatter(bpy.types.Operator):
    """把选中物体随机散布"""

    bl_idname = "ua.scatter"
    bl_label = "随机散布"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        n = asset_lib.scatter(
            context, props.scatter_count, props.scatter_radius,
            props.scatter_seed,
        )
        self.report({"INFO"}, f"已散布 {n} 个")
        return {"FINISHED"}


class UA_OT_grid_array(bpy.types.Operator):
    """选中物体网格阵列"""

    bl_idname = "ua.grid_array"
    bl_label = "网格阵列"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        n = asset_lib.grid_array(
            context, props.grid_cols, props.grid_rows, props.grid_spacing,
        )
        self.report({"INFO"}, f"网格阵列 {n} 个")
        return {"FINISHED"}


class UA_OT_ring_array(bpy.types.Operator):
    """选中物体环形阵列"""

    bl_idname = "ua.ring_array"
    bl_label = "环形阵列"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        n = asset_lib.ring_array(context, props.ring_count, props.ring_radius)
        self.report({"INFO"}, f"环形阵列 {n} 个")
        return {"FINISHED"}


class UA_OT_import_asset(bpy.types.Operator):
    """导入 FBX/OBJ/GLB 模型并自动归一化"""

    bl_idname = "ua.import_asset"
    bl_label = "导入模型并归一化"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.fbx;*.obj;*.glb;*.gltf")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            objs = asset_lib.import_normalize(context, self.filepath)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"导入 {len(objs)} 个对象并已归一化")
        return {"FINISHED"}


class UA_OT_text3d(bpy.types.Operator):
    """添加 3D 标题文字"""

    bl_idname = "ua.text3d"
    bl_label = "3D 标题文字"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uastudio
        obj = asset_lib.add_text3d(
            context, props.text_body, props.text_size, props.text_extrude,
        )
        self.report({"INFO"}, f"已添加文字「{props.text_body}」")
        return {"FINISHED"}


classes = (
    UA_OT_add_shape,
    UA_OT_scatter,
    UA_OT_grid_array,
    UA_OT_ring_array,
    UA_OT_import_asset,
    UA_OT_text3d,
)
