"""UI 层聚合。"""

from . import panels

registry = tuple(panels.classes)
