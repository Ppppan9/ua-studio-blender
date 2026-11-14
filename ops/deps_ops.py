"""依赖管理 Operator：扫描 / 启用 / 安装 / 修复全部。"""

from __future__ import annotations

import bpy

from ..core import deps


class UA_OT_deps_scan(bpy.types.Operator):
    """刷新前置插件状态"""

    bl_idname = "ua.deps_scan"
    bl_label = "扫描依赖状态"
    bl_options = {"REGISTER"}

    def execute(self, context):
        deps.scan(force=True)
        ready, total, _ = deps.summary()
        self.report({"INFO"}, "依赖就绪 " + str(ready) + "/" + str(total))
        return {"FINISHED"}


class UA_OT_deps_enable_online(bpy.types.Operator):
    """打开 Blender 在线访问开关（一键安装的前置条件）"""

    bl_idname = "ua.deps_enable_online"
    bl_label = "开启在线访问"
    bl_description = (
        "Blender 4.2+ 默认关闭联机访问；一键安装插件需要打开它"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        deps.enable_online_access()
        self.report({"INFO"}, "在线访问已开启，可一键安装插件")
        return {"FINISHED"}


class UA_OT_deps_install_one(bpy.types.Operator):
    """安装/启用单个前置插件"""

    bl_idname = "ua.deps_install_one"
    bl_label = "安装插件"
    bl_options = {"REGISTER"}

    key: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        dep = deps.get_entry(properties.key)
        return dep.purpose if dep else "安装/启用该插件"

    def execute(self, context):
        ok, msg = deps.install_dep(self.key)
        if msg == "NEED_ONLINE":
            self.report({"WARNING"}, "请先点「开启在线访问」再安装")
            return {"CANCELLED"}
        if ok:
            self.report({"INFO"}, msg)
            return {"FINISHED"}
        self.report({"ERROR"}, msg)
        return {"CANCELLED"}


class UA_OT_deps_fix_all(bpy.types.Operator):
    """启用+安装所有必需/推荐前置插件（可选插件不自动装）"""

    bl_idname = "ua.deps_fix_all"
    bl_label = "一键修复全部依赖"
    bl_options = {"REGISTER"}

    def execute(self, context):
        deps.scan()
        fixed, failed = [], []
        for dep in deps.DEPS:
            st = deps.get_status(dep.key)
            if st == deps.S_READY:
                continue
            if dep.level == "optional":
                continue
            ok, msg = deps.install_dep(dep.key)
            if msg == "NEED_ONLINE":
                self.report({"WARNING"}, "请先点「开启在线访问」再安装")
                return {"CANCELLED"}
            (fixed if ok else failed).append(f"{dep.name}:{msg}")
        if failed:
            self.report({"WARNING"}, "部分失败：" + "；".join(failed))
        else:
            self.report({"INFO"}, f"依赖就绪（{len(fixed)} 项处理完成）")
        return {"FINISHED"}


classes = (
    UA_OT_deps_scan,
    UA_OT_deps_enable_online,
    UA_OT_deps_install_one,
    UA_OT_deps_fix_all,
)