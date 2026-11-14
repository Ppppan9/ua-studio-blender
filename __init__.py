"""买量工坊 UA Studio —— 休闲游戏买量广告一键式制作工具箱。

Blender 扩展入口：注册属性组 / Operator / 面板。
"""

from __future__ import annotations

import bpy

from .core import deps, props, scene_lib, util
from .ops import registry as _ops
from .ui import registry as _panels

_VERSION_MIN = (4, 5, 0)


def _check_version() -> str | None:
    if bpy.app.version < _VERSION_MIN:
        return (
            f"买量工坊需要 Blender {_VERSION_MIN[0]}.{_VERSION_MIN[1]}+，"
            f"当前 {bpy.app.version_string}"
        )
    return None


def register() -> None:
    problem = _check_version()
    if problem:
        print(f"[UA Studio] {problem}")
    props.register()
    for cls in _ops:
        bpy.utils.register_class(cls)
    for cls in _panels:
        bpy.utils.register_class(cls)
    deps.scan()


def unregister() -> None:
    for cls in reversed(_panels):
        bpy.utils.unregister_class(cls)
    for cls in reversed(_ops):
        bpy.utils.unregister_class(cls)
    props.unregister()
