"""🎵 BGM 节拍检测：VSE 混音导出 → 能量包络 → 峰值 → 卡点标记。

原理：把 BGM 挂到 VSE 音频条（纯 API），用 Blender 自带的
「渲染音频」导出单声道 WAV，标准库 wave 读样本，算 RMS 能量
包络，动态阈值取上升沿为节拍点，换算帧号生成标记。
不依赖 ffmpeg 与任何第三方音频库。
"""

from __future__ import annotations

import math
import os
import re
import tempfile
import wave

_AUDIO_EXT_RE = re.compile(r"\.(mp3|wav|m4a|aac|ogg|flac)$", re.IGNORECASE)


def _check_audio_path(audio_path: str) -> None:
    if not audio_path or not os.path.isfile(audio_path):
        raise ValueError("音频文件不存在")
    if not _AUDIO_EXT_RE.search(audio_path):
        raise ValueError("仅支持 mp3/wav/m4a/aac/ogg/flac")


def _clear_old_beats(scene) -> int:
    n = 0
    for m in [m for m in scene.timeline_markers
              if m.name.startswith("beat_")]:
        scene.timeline_markers.remove(m)
        n += 1
    return n


def _export_mono_wav(context, audio_path: str, tmp_dir: str) -> str:
    """用 audasys 把 BGM 重采样导出单声道 16bit WAV，返回文件路径。

    纯 API 路径（aud.Sound.write），零子进程，支持全部 Blender 音频格式。
    """
    import aud

    sound = aud.Sound(audio_path).rechannel(aud.CHANNELS_MONO)
    wav_path = os.path.join(tmp_dir, "mix.wav")
    sound.write(
        wav_path,
        int(sound.specs[0]),
        aud.CHANNELS_MONO,
        aud.FORMAT_S16,
        aud.CONTAINER_WAV,
        aud.CODEC_PCM,
        0,
        0,
    )
    _ = context
    return wav_path
    se.strips.remove(strip)
    _ = old_strips
    return wav_path


def _read_wav_mono(path: str) -> tuple[list[float], int]:
    """读 WAV 返回 (归一化样本列表, 帧率)。"""
    wf = wave.open(path, "rb")
    framerate = wf.getframerate()
    nchannels = wf.getnchannels()
    width = wf.getsampwidth()
    raw = wf.readframes(wf.getnframes())
    wf.close()

    if width == 2:
        ints = []
        for i in range(0, len(raw), 2 * nchannels):
            # 取第一个声道，s16le
            v = int.from_bytes(raw[i: i + 2], "little", signed=True)
            ints.append(v / 32768.0)
        return ints, framerate
    if width == 1:
        return [b / 128.0 - 1.0 for b in raw[::nchannels]], framerate
    if width == 3:
        out = []
        for i in range(0, len(raw), 3 * nchannels):
            v = int.from_bytes(raw[i: i + 3], "little", signed=True)
            out.append(v / 8388608.0)
        return out, framerate
    return [], framerate


def detect_beats(samples: list[float], framerate: int,
                 duration_frames: int, fps: int,
                 sensitivity: float = 1.4,
                 min_gap_frames: int = 6) -> list[int]:
    """从样本序列检测节拍，返回帧号列表（1 起，限片长内）。"""
    if len(samples) < framerate // 4:
        return []
    # 10ms 窗口 RMS 能量包络
    win = max(1, framerate // 100)
    env = []
    for i in range(0, len(samples) - win + 1, win):
        acc = 0.0
        for s in samples[i: i + win]:
            acc += s * s
        env.append(math.sqrt(acc / win))
    if len(env) < 3:
        return []

    mean = sum(env) / len(env)
    var = sum((e - mean) ** 2 for e in env) / len(env)
    threshold = mean + sensitivity * math.sqrt(var)

    # 上升沿过阈 = 节拍；按最小间隔去重
    frames = []
    last = -min_gap_frames
    samples_per_frame = framerate / max(1, fps)
    for idx, e in enumerate(env):
        if e < threshold:
            continue
        prev = env[idx - 1] if idx else 0.0
        if prev >= threshold:
            continue
        frame = int(idx * win / samples_per_frame) + 1
        if frame <= last + min_gap_frames:
            continue
        if frame > duration_frames:
            break
        frames.append(frame)
        last = frame
    return frames


def auto_beats_from_audio(context, audio_path: str,
                          sensitivity: float = 1.4,
                          max_beats: int = 24) -> int:
    """导入 BGM 自动生成卡点标记（先清旧 beat_ 标记）。返回标记数。"""
    _check_audio_path(audio_path)
    scene = context.scene
    _clear_old_beats(scene)

    with tempfile.TemporaryDirectory(prefix="ua_beats_") as tmp:
        wav_path = _export_mono_wav(context, audio_path, tmp)
        if not os.path.exists(wav_path):
            raise ValueError("音频重采样导出失败")
        samples, framerate = _read_wav_mono(wav_path)

    frames = detect_beats(
        samples, framerate, scene.frame_end, scene.render.fps, sensitivity)
    if len(frames) > max_beats:
        step = len(frames) / max_beats
        frames = [frames[int(i * step)] for i in range(max_beats)]
    for fr in frames:
        scene.timeline_markers.new("beat_" + str(fr), frame=fr)
    return len(frames)
