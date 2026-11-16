"""买量工坊 UA Studio · core 层。

无 bpy.types 注册的纯逻辑库，Operator 与 UI 只做薄封装。
"""

from . import util
from . import deps
from . import scene_lib
from . import asset_lib
from . import material_lib
from . import physics_cloth
from . import fluid_lib
from . import render_lib
from . import endcard_lib
from . import game_fx_lib
from . import shot_lib
from . import template_lib
from . import quality_lib
from . import beat_detect
from . import candy_render

__all__ = [
    "util", "deps", "scene_lib", "asset_lib", "material_lib",
    "physics_cloth", "fluid_lib", "render_lib", "endcard_lib",
    "game_fx_lib", "shot_lib", "template_lib", "quality_lib",
    "beat_detect", "candy_render",
]
