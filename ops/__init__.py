"""Operator 层聚合。"""

from . import (
    deps_ops,
    scene_ops,
    asset_ops,
    material_ops,
    anim_ops,
    camera_ops,
    physics_ops,
    render_ops,
    game_ops,
    shot_ops,
    quality_ops,
    candy_ops,
)

classes = (
    *deps_ops.classes,
    *scene_ops.classes,
    *asset_ops.classes,
    *material_ops.classes,
    *anim_ops.classes,
    *camera_ops.classes,
    *physics_ops.classes,
    *render_ops.classes,
    *game_ops.classes,
    *shot_ops.classes,
    *quality_ops.classes,
    *candy_ops.classes,
)

registry = tuple(classes)  # 顶层 __init__ 遍历注册
