"""③ 材质 Operator：一键赋材质。"""

from __future__ import annotations

import bpy

from ..core import material_lib


class UA_OT_apply_material(bpy.types.Operator):
    """给选中物体一键赋材质"""

    bl_idname = "ua.apply_material"
    bl_label = "一键赋材质"
    bl_options = {"REGISTER", "UNDO"}

    key: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.uastudio
        try:
            count = material_lib.apply_to_selection(
                context, self.key, props.mat_color
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"已为 {count} 个物体赋材质")
        return {"FINISHED"}


classes = (UA_OT_apply_material,)
