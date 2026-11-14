"""📦 交付包：一键收集全部投放产出并打包 zip。

流程：批量渲染（正片+结尾卡 mp4）→ 封面图 → 音效清单 →
blend 副本 → 全部归入交付子目录 → zip。投放对接一步到位。
"""

from __future__ import annotations

import os
import shutil

import bpy

from . import render_lib, shot_lib

_DELIVERY_DIR = "delivery"


def export_delivery_package(context) -> str:
    """一键交付包：渲染全部场景 + 封面 + 音效清单 + 工程副本 → zip。

    返回 zip 路径。产物目录：<out_dir>/delivery/
    """
    scene = context.scene
    props = scene.uastudio
    out_root = bpy.path.abspath(props.out_dir.rstrip("/"))
    stamp = render_lib._safe_name(scene.name)
    delivery_dir = os.path.join(out_root, _DELIVERY_DIR + "_" + stamp)
    os.makedirs(delivery_dir, exist_ok=True)

    # 1. 批量渲染（正片 + 结尾卡，mp4 或序列按 out_format）
    render_lib.batch_render(context)

    # 2. 封面图
    render_lib.export_cover(context, props.cover_frame)

    # 3. 音效需求清单
    try:
        shot_lib.export_sfx_list(context, props.out_dir)
    except (ValueError, OSError):
        pass  # 音效清单失败不阻塞交付

    # 4. 工程副本
    blend_path = os.path.join(delivery_dir, "project.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)

    # 5. 把 mp4 / 封面 / 音效清单收进交付目录（渲染输出在外层）
    moved = []
    for name in sorted(os.listdir(out_root)):
        src = os.path.join(out_root, name)
        if src.startswith(delivery_dir):
            continue
        keep = (
            name.endswith(".mp4")
            or ("cover" in name and name.endswith(".png"))
            or name == "sfx_list.txt"
        )
        if keep and os.path.isfile(src):
            shutil.move(src, os.path.join(delivery_dir, name))
            moved.append(name)

    # 6. 打包 zip
    zip_base = os.path.join(out_root, "delivery_" + stamp)
    zip_path = shutil.make_archive(zip_base, "zip", delivery_dir)
    _ = moved
    return zip_path
