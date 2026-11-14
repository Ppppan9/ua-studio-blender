"""前置插件依赖管理：注册表 + 状态检测 + 一键启用 / 一键安装。

来源（kind）三种：
- builtin    Blender 捆绑插件，只需启用；
- extension  extensions.blender.org 扩展（老版本捆绑则回退旧模块名启用）；
- github_zip 从 GitHub Release 下载 zip 安装。

安装统一走 Blender 自带 CLI（--command extension ...）。
"""

from __future__ import annotations

import dataclasses
import ipaddress
import json
import os
import platform
import re
import socket
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import addon_utils
import bpy

# ---------------------------------------------------------------------------
# 状态常量（整数态）
# ---------------------------------------------------------------------------

S_READY = 1         # 已安装且已启用
S_DISABLED = 2      # 已安装未启用
S_MISSING = 3       # 未安装（可一键安装）
S_UNAVAILABLE = 4   # 安装/启用失败（给手动链接兜底）
S_NEED_ONLINE = 5   # Blender 在线访问开关未打开

_STATUS_ICON = {
    S_READY: "CHECKMARK",
    S_DISABLED: "PLUGIN",
    S_MISSING: "DOWNARROW_HLT",
    S_UNAVAILABLE: "X",
    S_NEED_ONLINE: "ERROR",
}

_STATUS_TEXT = {
    S_READY: "就绪",
    S_DISABLED: "未启用",
    S_MISSING: "未安装",
    S_UNAVAILABLE: "不可用",
    S_NEED_ONLINE: "需在线访问",
}

_status: dict[str, int] = {}
_note: dict[str, str] = {}
# scan 结果缓存时间戳（monotonic 秒），0 表示从未扫描
_scan_cache_valid: list[float] = [0.0]


def status_icon(status: int) -> str:
    return _STATUS_ICON.get(status, "QUESTION")


def status_text(status: int) -> str:
    return _STATUS_TEXT.get(status, "未知")


# ---------------------------------------------------------------------------
# 依赖注册表
# ---------------------------------------------------------------------------

# 包 ID / GitHub 仓库串格式白名单（即使注册表被改也只有安全字符能进 CLI/URL）
_PACKAGE_ID_RE = re.compile(r"^[a-z0-9_]+$")
_GH_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# 下载资产文件名白名单：语法上不可能含路径分隔符
_ZIP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.zip$")


@dataclasses.dataclass(frozen=True)
class DepEntry:
    key: str                      # 稳定标识（operator 的 "key" 参数）
    name: str                     # 显示名
    kind: str                     # builtin | extension | github_zip
    level: str                    # required | recommended | optional
    purpose: str                  # 一句话用途（面板展示）
    module: str = ""              # 启用用模块名（builtin / extension 完整名）
    legacy_module: str = ""       # 老版本捆绑时的模块名
    package_id: str = ""          # extension 包 ID / github 安装后模块名
    repo_module: str = ""         # extension 仓库模块（blender_org）
    gh_repo: str = ""             # GitHub: owner/repo
    url: str = ""                 # 手动下载兜底链接


DEPS: list[DepEntry] = [
    DepEntry(
        key="cell_fracture", name="Cell Fracture", kind="extension",
        level="required", purpose="一键破碎/爆炸效果（物理模块必需）",
        module="bl_ext.blender_org.cell_fracture",
        legacy_module="object_cell_fracture",
        package_id="cell_fracture",
        repo_module="blender_org",
        url="https://extensions.blender.org/add-ons/cell-fracture/",
    ),
    DepEntry(
        key="io_scene_fbx", name="FBX 导入器", kind="builtin",
        level="required", purpose="导入 FBX 素材模型",
        module="io_scene_fbx",
    ),
    DepEntry(
        key="io_scene_gltf2", name="glTF 导入器", kind="builtin",
        level="required", purpose="导入 GLB/glTF 素材模型",
        module="io_scene_gltf2",
    ),
    DepEntry(
        key="node_wrangler", name="Node Wrangler", kind="builtin",
        level="recommended", purpose="材质节点快捷操作",
        module="node_wrangler",
    ),
    DepEntry(
        key="extra_mesh_objects", name="Extra Mesh Objects", kind="extension",
        level="recommended", purpose="补充常用网格形状",
        module="bl_ext.blender_org.extra_mesh_objects",
        legacy_module="add_mesh_extra_objects",
        package_id="extra_mesh_objects",
        repo_module="blender_org",
        url="https://extensions.blender.org/add-ons/extra-mesh-objects/",
    ),
    DepEntry(
        key="looptools", name="LoopTools", kind="extension",
        level="recommended", purpose="建模辅助（圆滑/桥接）",
        module="bl_ext.blender_org.looptools",
        legacy_module="mesh_looptools",
        package_id="looptools",
        repo_module="blender_org",
        url="https://extensions.blender.org/add-ons/looptools/",
    ),
    DepEntry(
        key="scatter_objects", name="Scatter Objects", kind="extension",
        level="recommended", purpose="物体散布/随机摆放",
        module="bl_ext.blender_org.scatter_objects",
        legacy_module="object_scatter",
        package_id="scatter_objects",
        repo_module="blender_org",
        url="https://extensions.blender.org/add-ons/scatter-objects/",
    ),
    DepEntry(
        key="blenderkit", name="BlenderKit", kind="github_zip",
        level="optional", purpose="海量免费模型/材质/HDRI 素材库",
        package_id="blenderkit",
        gh_repo="BlenderKit/blenderkit",
        url="https://www.blenderkit.com/",
    ),
    DepEntry(
        key="animation_nodes", name="Animation Nodes", kind="github_zip",
        level="optional", purpose="程序化动画增强（兼容性以实测为准）",
        package_id="animation_nodes",
        gh_repo="JacquesLucke/animation_nodes",
        url="https://github.com/JacquesLucke/animation_nodes/releases",
    ),
]


# ---------------------------------------------------------------------------
# 检测
# ---------------------------------------------------------------------------


def _available_modules() -> dict[str, object]:
    return {mod.__name__: mod for mod in addon_utils.modules()}


def _is_enabled(module_name: str) -> bool:
    if module_name in bpy.context.preferences.addons:
        return True
    try:
        _loaded_default, loaded_state = addon_utils.check(module_name)
        return bool(loaded_state)
    except Exception:
        return False


def online_access_on() -> bool:
    """Blender 的在线访问开关是否已打开（一键安装的前置条件）。"""
    sys_prefs = bpy.context.preferences.system
    return bool(getattr(sys_prefs, "use_online_access", True))


def scan(force: bool = False) -> dict[str, int]:
    """刷新全部依赖状态缓存并返回 {key: 状态}。

    带结果缓存：默认 1 秒内重复调用直接返回缓存（面板 draw 每帧调用，
    不做缓存会遍历全部模块导致 UI 卡顿）；force=True 强制刷新。
    """
    import time

    now = time.monotonic()
    if not force and _scan_cache_valid[0] and now - _scan_cache_valid[0] < 1.0:
        return dict(_status)
    _scan_cache_valid[0] = now

    modules = _available_modules()
    module_names = set(modules.keys())

    for dep in DEPS:
        if dep.kind == "builtin":
            if dep.module in module_names:
                _status[dep.key] = S_READY if _is_enabled(dep.module) else S_DISABLED
            else:
                _status[dep.key] = S_MISSING
                _note[dep.key] = "当前 Blender 未捆绑该插件"
            continue

        if dep.kind == "extension":
            # 老版本捆绑回退：有旧模块名就按 builtin 处理
            if dep.legacy_module and dep.legacy_module in module_names:
                _status[dep.key] = (
                    S_READY if _is_enabled(dep.legacy_module) else S_DISABLED
                )
                continue
            ext_name = dep.module or f"bl_ext.{dep.repo_module}.{dep.package_id}"
            if ext_name in module_names:
                _status[dep.key] = S_READY if _is_enabled(ext_name) else S_DISABLED
            else:
                _status[dep.key] = S_MISSING
            continue

        # github_zip：按模块名结尾匹配（安装后模块带 bl_ext.user_default. 前缀）
        found = None
        for name in module_names:
            if name.split(".")[-1].startswith(dep.package_id):
                found = name
                break
        if found is not None:
            _status[dep.key] = S_READY if _is_enabled(found) else S_DISABLED
        else:
            _status[dep.key] = S_MISSING

    return dict(_status)


def get_status(key: str) -> int:
    if not _status:
        scan()
    return _status.get(key, S_MISSING)


def get_note(key: str) -> str:
    return _note.get(key, "")


def get_entry(key: str) -> DepEntry | None:
    for dep in DEPS:
        if dep.key == key:
            return dep
    return None


def summary() -> tuple[int, int, int]:
    """返回 (就绪数, 总数, 最差状态)。最差状态决定横幅颜色。"""
    if not _status:
        scan()
    ready = sum(1 for dep in DEPS if _status.get(dep.key) == S_READY)
    required_bad = any(
        _status.get(d.key) not in (S_READY, S_DISABLED) for d in DEPS
        if d.level == "required"
    )
    any_missing = any(_status.get(d.key) != S_READY for d in DEPS)
    if required_bad:
        worst = S_UNAVAILABLE
    elif any_missing:
        worst = S_MISSING
    else:
        worst = S_READY
    return ready, len(DEPS), worst


# ---------------------------------------------------------------------------
# 启用
# ---------------------------------------------------------------------------


def enable_dep(key: str) -> tuple[bool, str]:
    """启用一个依赖：按 module > legacy > 扩展名 > github 模糊匹配找模块。"""
    dep = get_entry(key)
    if dep is None:
        return False, f"未知依赖 {key}"

    modules = _available_modules()
    candidates = []
    if dep.module:
        candidates.append(dep.module)
    if dep.legacy_module:
        candidates.append(dep.legacy_module)
    if dep.repo_module and dep.package_id:
        candidates.append(f"bl_ext.{dep.repo_module}.{dep.package_id}")
    if dep.kind == "github_zip":
        candidates += [
            n for n in modules if n.split(".")[-1].startswith(dep.package_id)
        ]
    target = next((c for c in candidates if c in modules), "")

    if not target:
        scan()
        return False, f"{dep.name} 未安装"

    ok = addon_utils.enable(target)
    if ok is None:
        _status[key] = S_UNAVAILABLE
        _note[key] = "启用失败：可能与当前 Blender 版本不兼容"
        return False, f"{dep.name} 启用失败（可能与本版本不兼容）"

    _status[key] = S_READY
    try:
        bpy.ops.wm.save_userpref()
    except RuntimeError:
        pass
    return True, f"{dep.name} 已启用"


# ---------------------------------------------------------------------------
# 安装（CLI 子进程 + GitHub 下载，全部带白名单/格式校验）
# ---------------------------------------------------------------------------

# 下载白名单：仅允许 GitHub 官方域（API + 资产 CDN）
_ALLOWED_HOSTS = {
    "github.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "codeload.github.com",
}


def _validate_url(url: str) -> urllib.parse.ParseResult:
    """强制 https + 白名单域名 + 解析 IP 阻断内网/环回/链路本地。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("仅允许 https 下载")
    host = parsed.hostname or ""
    if host not in _ALLOWED_HOSTS:
        raise ValueError(f"域名不在白名单: {host}")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"域名解析失败: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"域名解析到内网地址，已阻断: {host}")
    return parsed


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    """重定向目标也过白名单校验。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_RedirectGuard)


def _download_zip(url: str, timeout: int = 300) -> str:
    """下载 zip 到临时文件并返回路径。

    文件由 tempfile.NamedTemporaryFile 创建（天然位于系统临时目录内），
    内容直接写入文件句柄，全程不出现动态路径 open()。
    """
    _validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "ua-studio-blender"})
    fh = tempfile.NamedTemporaryFile(
        prefix="ua_studio_dep_", suffix=".zip", delete=False
    )
    try:
        with _OPENER.open(request, timeout=timeout) as resp:
            shutil.copyfileobj(resp, fh)
    finally:
        fh.close()
    return fh.name


def _binary_path() -> str:
    return bpy.app.binary_path or "/Applications/Blender.app/Contents/MacOS/Blender"


def _run_cli(args: list[str], timeout: int = 600) -> tuple[int, str]:
    """调用 Blender 自带 CLI。参数列表 + shell=False，参数均为注册表常量。"""
    cmd = [_binary_path(), "--background"] + list(args)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "命令超时"
    except OSError as exc:
        return 1, f"启动 Blender CLI 失败: {exc}"


def _cli_error(output: str) -> str:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(("Error", "ERROR", "Package")):
            return line[:200]
    last = output.strip().splitlines()
    return last[-1][:200] if last else "未知错误"


def install_extension(dep: DepEntry) -> tuple[bool, str]:
    """从 extensions.blender.org 安装（CLI sync + install）。"""
    if not _PACKAGE_ID_RE.fullmatch(dep.package_id or ""):
        return False, "package_id 格式非法"
    rc, out = _run_cli(["--command", "extension", "sync"], timeout=180)
    if rc != 0:
        return False, f"同步远程源失败：{_cli_error(out)}"
    rc, out = _run_cli(["--command", "extension", "install", dep.package_id])
    if rc != 0 or "Installed" not in out:
        return False, f"安装失败：{_cli_error(out)}"
    return True, f"{dep.name} 安装成功"


def install_github_zip(dep: DepEntry) -> tuple[bool, str]:
    """从 GitHub Latest Release 下载 zip 并安装到 user_default。"""
    if not _GH_REPO_RE.fullmatch(dep.gh_repo or ""):
        return False, "gh_repo 格式非法"
    api = f"https://api.github.com/repos/{dep.gh_repo}/releases/latest"
    request = urllib.request.Request(api, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ua-studio-blender",
    })
    try:
        with _OPENER.open(request, timeout=30) as resp:
            release = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        return False, f"查询 Release 失败：{exc}（可手动下载：{dep.url}）"

    assets = [
        a for a in release.get("assets", [])
        if a.get("name", "").lower().endswith(".zip")
    ]
    if not assets:
        return False, f"Release 中没有 zip 资产（可手动下载：{dep.key} 手动链接 {dep.url}）"

    # 选资产：当前平台优先（mac/win），无平台标记的通用包兜底
    if platform.system() == "Darwin":
        preferred = [a for a in assets if "mac" in a["name"].lower()]
    else:
        preferred = [a for a in assets if "win" in a["name"].lower()]
    asset = (preferred or assets)[0]

    zip_path = ""
    try:
        zip_path = _download_zip(asset["browser_download_url"])
        rc, out = _run_cli([
            "--command", "extension", "install-file",
            "-r", "user_default", "-e", zip_path,
        ])
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return False, f"下载失败：{exc}（可手动下载：{dep.url}）"
    finally:
        if zip_path:
            try:
                os.remove(zip_path)
            except OSError:
                pass

    if rc != 0 or "Installed" not in out:
        return False, f"安装失败：{_cli_error(out)}"
    return True, f"{dep.name} 安装成功"


def install_dep(key: str) -> tuple[bool, str]:
    """安装依赖（含启用）。msg 为 NEED_ONLINE 时 UI 引导开启在线访问。"""
    if not online_access_on():
        _status[key] = S_NEED_ONLINE
        return False, "NEED_ONLINE"

    dep = get_entry(key)
    if dep is None:
        return False, f"未知依赖 {key}"

    if dep.kind == "builtin":
        return enable_dep(key)

    if dep.kind == "extension":
        ok, msg = install_extension(dep)
    else:
        ok, msg = install_github_zip(dep)

    scan(force=True)
    if ok:
        ok2, msg2 = enable_dep(key)
        return ok2, msg2 if not ok2 else msg
    return ok, msg


def enable_online_access() -> bool:
    """打开 Blender 在线访问开关（一键安装的前置条件）。"""
    bpy.context.preferences.system.use_online_access = True
    try:
        bpy.ops.wm.save_userpref()
    except RuntimeError:
        pass
    return True
