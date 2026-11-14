"""⑦ 渲染库：输出预设 / 一键渲染 / 批量渲染。

渲染统一走 CLI 子进程（先存副本再 blender -b 渲染）：
规避同会话内新建对象的 depsgraph 时序怪癖，也更稳、可并行。
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile

import bpy

# CLI 数字参数白名单（帧号等）
_NUM_RE = re.compile(r"^\d{1,6}$")
# 输出文件路径白名单（中文等字符统一清洗）
_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")


def _safe_name(name: str) -> str:
    """场景名/tag 清洗为安全文件名（非白名单字符→下划线）。空串返回空串。"""
    if not name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
    return cleaned.strip("_") or "scene"


def apply_output_preset(scene, kind: str, out_dir: str, transparent: bool) -> None:
    """输出预设。kind: 'mp4'（H.264 成片）| 'png_seq'（透明序列帧）。

    mp4 路径：Blender 出 PNG 序列（部分构建无内置 ffmpeg），渲染完成后
    由 render_current 调系统 ffmpeg 转码；无系统 ffmpeg 时回落为 PNG 序列。
    """
    r = scene.render
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    if kind == "png_seq":
        r.image_settings.color_mode = "RGBA"
        r.film_transparent = True
        r.filepath = out_dir.rstrip("/") + "/" + scene.name + "_frame_"
    else:
        r.image_settings.color_mode = "RGB"
        r.film_transparent = False
        r.filepath = out_dir.rstrip("/") + "/" + scene.name + "_frame_"


def _cli_render(tmp_blend: str, mode: str, frame_s: str,
                scene_name: str = "") -> tuple[int, str]:
    binary = bpy.app.binary_path or "/Applications/Blender.app/Contents/MacOS/Blender"
    if not _NUM_RE.fullmatch(frame_s):
        raise RuntimeError("非法帧号")
    if not _SAFE_PATH_RE.fullmatch(tmp_blend):
        raise RuntimeError("任务文件路径含非白名单字符")
    args = [binary, "-b", tmp_blend]
    if scene_name:
        # 场景名仅允许安全字符（防注入 + 保证 -S 精确匹配）
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", scene_name):
            raise RuntimeError("场景名含非白名单字符，无法 CLI 渲染")
        args += ["-S", scene_name]
    if mode == "still":
        args += ["-f", frame_s]
    else:
        args += ["-a"]
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=3600, shell=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "渲染超时"
    except OSError as exc:
        return 1, "启动渲染失败: " + str(exc)


def render_current(context, still: bool = False, scene=None,
                   tag: str = "") -> str:
    """渲染指定场景（CLI 子进程，-S 指定场景名）。still=True 只出当前帧。

    tag 追加在输出文件名后（多尺寸矩阵/封面导出用）。
    """
    scene = scene or context.scene
    props = scene.uastudio
    # 结尾卡场景单渲染兜底：输出设置跟随主场景（避免落默认 //renders）
    from . import endcard_lib
    if scene.name == endcard_lib.ENDCARD_SCENE:
        main = next((s for s in bpy.data.scenes
                     if s.name != endcard_lib.ENDCARD_SCENE), None)
        if main is not None:
            props.out_dir = main.uastudio.out_dir
            props.out_format = main.uastudio.out_format
            props.transparent = main.uastudio.transparent
    apply_output_preset(
        scene, props.out_format, props.out_dir, props.transparent
    )
    name = _safe_name(scene.name) + _safe_name(tag)
    out_abs = bpy.path.abspath(
        props.out_dir.rstrip("/") + "/" + name + "_frame_"
    )
    scene.render.filepath = out_abs
    out_dir = os.path.dirname(out_abs) or "/tmp"
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_blend = os.path.join(tmp, "render_job.blend")
        bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)
        frame_s = str(int(scene.frame_current)) if still else "1"
        rc, out = _cli_render(
            tmp_blend, "still" if still else "anim", frame_s,
            scene_name=scene.name,
        )
    if rc != 0:
        raise RuntimeError(out.strip().splitlines()[-1][:200] if out else "未知错误")

    # mp4 档：PNG 序列 → 系统 ffmpeg 转码；无 ffmpeg 回落 PNG 序列
    if props.out_format == "mp4" and not still:
        mp4_path = out_dir + "/" + name + ".mp4"
        ok, msg = _transcode_mp4(out_abs, mp4_path, scene.render.fps)
        if ok:
            return mp4_path
        print("[UA Studio] mp4 转码失败，回落 PNG 序列:", msg)
        return out_abs
    if still:
        return out_abs + "%04d.png" % int(scene.frame_current)
    return out_abs


def _transcode_mp4(frames_prefix: str, out_mp4: str, fps: int) -> tuple[bool, str]:
    """用系统 ffmpeg 把 PNG 序列转成 H.264 mp4（路径全部过白名单校验）。"""
    import shutil

    for s in (frames_prefix, out_mp4):
        if not _SAFE_PATH_RE.fullmatch(s):
            return False, "输出路径含非白名单字符"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, "未找到系统 ffmpeg"
    fps = int(fps)
    if not (1 <= fps <= 120):
        return False, "非法帧率"
    # 常见帧率字面量表（避免动态字符串进命令行）
    fps_str = {24: "24", 25: "25", 30: "30", 48: "48", 60: "60"}.get(fps, "30")
    frames = frames_prefix + "%04d.png"
    args = [
        ffmpeg, "-y",
        "-framerate", fps_str,
        "-i", frames,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-movflags", "+faststart",
        out_mp4,
    ]
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=1800, shell=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, "ffmpeg 转码失败: " + str(exc)
    if proc.returncode != 0:
        return False, "ffmpeg 转码失败: " + (proc.stderr or "")[-200:]
    return True, out_mp4


# ---------------------------------------------------------------------------
# 多尺寸矩阵与封面
# ---------------------------------------------------------------------------

# 投放三画幅：tag → (分辨率, 相机预设键)
_SIZE_MATRIX = (
    ("9x16", (1080, 1920), "9:16"),
    ("1x1", (1080, 1080), "1:1"),
    ("16x9", (1920, 1080), "16:9"),
)


def render_size_matrix(context) -> int:
    """多尺寸矩阵：同一场景按 9:16 / 1:1 / 16:9 各渲染一条，
    相机机位按画幅自动适配。渲染完成恢复原分辨率与机位。"""
    from . import util

    scene = context.scene
    cam = scene.camera
    if cam is None:
        raise ValueError("场景里没有相机")
    orig_res = (scene.render.resolution_x, scene.render.resolution_y)
    orig_loc = tuple(cam.location)
    orig_rot = tuple(cam.rotation_euler)

    count = 0
    errors = []
    for tag, (w, h), preset_key in _SIZE_MATRIX:
        try:
            scene.render.resolution_x = w
            scene.render.resolution_y = h
            loc, target = util.CAMERA_PRESETS[preset_key]
            cam.location = loc
            util.look_at(cam, target)
            render_current(context, still=False, scene=scene, tag="_" + tag)
            count += 1
        except RuntimeError as exc:
            errors.append(tag + ": " + str(exc))
    scene.render.resolution_x, scene.render.resolution_y = orig_res
    cam.location = orig_loc
    cam.rotation_euler = orig_rot
    if errors:
        raise RuntimeError("；".join(errors))
    return count


def export_cover(context, frame: int) -> str:
    """导出投放封面：指定帧渲染为 PNG（cover 命名）。"""
    scene = context.scene
    saved_frame = scene.frame_current
    scene.frame_set(frame)
    try:
        out = render_current(context, still=True, scene=scene, tag="_cover")
    finally:
        scene.frame_set(saved_frame)
    return out


def batch_render(context) -> int:
    """批量渲染全场景（每场景独立输出，命名规范自动落盘）。

    输出设置以「主场景」（第一个非结尾卡场景）为准，统一同步到其余场景。
    场景数 ≤2 时双路并行：主线程先预置好两场景的输出并保存单份副本，
    再用线程池同时跑两个 CLI 子进程（子进程独立于 bpy 主线程，安全）；
    更多场景退回串行避免 GPU 争抢。
    """
    import time
    from concurrent.futures import ThreadPoolExecutor

    from . import endcard_lib

    ref = next(
        (s for s in bpy.data.scenes if s.name != endcard_lib.ENDCARD_SCENE),
        context.scene,
    )
    ref_props = ref.uastudio
    scenes = list(bpy.data.scenes)
    errors: list[str] = []
    timings: dict[str, float] = {}

    # 主线程预置：输出设置同步 + 各场景独立输出路径
    jobs: list[tuple[bpy.types.Scene, str]] = []
    for scene in scenes:
        s_props = scene.uastudio
        if scene is not ref:
            s_props.out_dir = ref_props.out_dir
            s_props.out_format = ref_props.out_format
            s_props.transparent = ref_props.transparent
        name = _safe_name(scene.name)
        out_abs = bpy.path.abspath(
            s_props.out_dir.rstrip("/") + "/" + name + "_frame_"
        )
        scene.render.filepath = out_abs
        jobs.append((scene, out_abs))
    out_root = os.path.dirname(jobs[0][1]) or "/tmp"
    os.makedirs(out_root, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_blend = os.path.join(tmp, "render_job.blend")
        bpy.ops.wm.save_as_mainfile(filepath=tmp_blend, copy=True)

        def _job(scene, out_abs):
            t0 = time.monotonic()
            rc, out = _cli_render(
                tmp_blend, "anim", "1", scene_name=scene.name,
            )
            if rc != 0:
                raise RuntimeError(out.strip().splitlines()[-1][:200]
                                   if out else "未知错误")
            if scene.uastudio.out_format == "mp4":
                mp4 = os.path.dirname(out_abs) + "/" + _safe_name(
                    scene.name) + ".mp4"
                ok, msg = _transcode_mp4(out_abs, mp4, scene.render.fps)
                if not ok:
                    print("[UA Studio] mp4 转码失败:", msg)
            timings[scene.name] = time.monotonic() - t0

        if len(scenes) <= 2:
            # 仅子进程进线程（bpy 数据操作全部已在主线程完成）
            with ThreadPoolExecutor(max_workers=len(scenes)) as pool:
                futures = {pool.submit(_job, s, oa): s for s, oa in jobs}
                for fut, s in futures.items():
                    try:
                        fut.result()
                    except RuntimeError as exc:
                        errors.append(s.name + ": " + str(exc))
        else:
            for scene, out_abs in jobs:
                try:
                    _job(scene, out_abs)
                except RuntimeError as exc:
                    errors.append(scene.name + ": " + str(exc))

    if errors:
        raise RuntimeError("；".join(errors))
    batch_render.last_timings = dict(timings)
    return len(scenes)