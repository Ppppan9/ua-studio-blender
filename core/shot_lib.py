"""🎬 分镜库：分镜 CRUD / 跳转 / 音效需求清单导出。

买量广告的标准结构是 3~5 段：Hook → 玩法展示 → 爽点奖励 → 收尾。
分镜管理器把这些段落显式管理起来，方便跳转编辑和分段渲染。
"""

from __future__ import annotations

import os
import re

import bpy

# 输出路径白名单（与 render_lib 同规则）
_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")

# 默认分镜结构（15 秒 30fps）
DEFAULT_SHOTS = (
    ("Hook 钩子", 1, 90),
    ("玩法展示", 91, 300),
    ("爽点奖励", 301, 390),
    ("收尾", 391, 450),
)


def _shots(context) -> bpy.types.CollectionProperty:
    return context.scene.uastudio.shots


def setup_default(context) -> int:
    """按 15 秒标准结构生成默认分镜（覆盖现有）。"""
    shots = _shots(context)
    shots.clear()
    for name, start, end in DEFAULT_SHOTS:
        item = shots.add()
        item.name = name
        item.start = start
        item.end = end
    return len(shots)


def add_shot(context, name: str, start: int, end: int) -> int:
    shots = _shots(context)
    item = shots.add()
    item.name = name or ("分镜 " + str(len(shots)))
    item.start = max(1, int(start))
    item.end = max(item.start + 1, int(end))
    return len(shots)


def goto_shot(context, index: int) -> tuple[int, int]:
    """跳转到分镜：渲染区间设为该分镜，时间轴跳到起点。"""
    shots = _shots(context)
    if index < 0 or index >= len(shots):
        raise ValueError("分镜序号不存在")
    item = shots[index]
    scene = context.scene
    scene.frame_start = item.start
    scene.frame_end = item.end
    scene.frame_set(item.start)
    return item.start, item.end


def remove_shot(context, index: int) -> None:
    shots = _shots(context)
    if 0 <= index < len(shots):
        shots.remove(index)


def export_sfx_list(context, out_dir: str) -> str:
    """导出音效需求清单 TXT（按分镜与卡点标记，供后期对轨）。"""
    scene = context.scene
    fps = max(1, scene.render.fps)
    lines = ["音效需求清单 — " + scene.name,
             "片长: " + str(scene.frame_start) + "-" + str(scene.frame_end)
             + " 帧 @ " + str(fps) + "fps", ""]

    shots = _shots(context)
    if len(shots):
        lines.append("== 分镜 ==")
        for i, item in enumerate(shots):
            sec0 = round(item.start / fps, 1)
            sec1 = round(item.end / fps, 1)
            lines.append(str(i + 1) + ". " + item.name
                         + "  [" + str(item.start) + "-" + str(item.end)
                         + " 帧 | " + str(sec0) + "-" + str(sec1) + "s]")
        lines.append("")

    beats = [m for m in scene.timeline_markers if m.name.startswith("beat_")]
    if beats:
        lines.append("== 卡点（CSV 列：帧,秒,建议类型,建议音量）==")
        types = ["点击音", "收集音", "消除音", "成功音"]
        for i, m in enumerate(sorted(beats, key=lambda x: x.frame)):
            sec = round(m.frame / fps, 2)
            vol = "0.6" if i % 3 else "0.9"
            lines.append(str(m.frame) + "," + str(sec) + ","
                         + types[i % len(types)] + "," + vol)
        lines.append("")

    lines.append("== 通用建议 ==")
    lines.append("- BGM: 轻快节奏，卡点处重拍")
    lines.append("- 消除/收集: 短促「叮」；金币: 金属碰撞；破碎: 低频碎裂")
    lines.append("- 结尾卡: 下载按钮「咚」+ 品牌音")

    out_abs = bpy.path.abspath(out_dir.rstrip("/"))
    if not _SAFE_PATH_RE.fullmatch(out_abs):
        raise ValueError("输出目录含非白名单字符，请使用纯 ASCII 路径")
    os.makedirs(out_abs, exist_ok=True)
    from pathlib import Path
    out_path = Path(out_abs) / "sfx_list.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
