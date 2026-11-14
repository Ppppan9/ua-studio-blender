"""🎬 一键广告模板：三套完整分镜工程，一键生成后可自由改。

每个模板 = 完整买量广告：工程搭建 → 素材编排 → 假玩法动作 →
HUD/运镜/粒子 → 分镜与卡点 → 结尾卡场景。生成后所有元素皆可改。
"""

from __future__ import annotations

import math

import bpy

from . import (
    anim_lib,
    asset_lib,
    endcard_lib,
    game_fx_lib,
    material_lib,
    physics_lib,
    scene_lib,
    shot_lib,
    util,
)

# 分镜编排节奏（帧）
HOOK_END = 90
PLAY_MID = 210
PLAY_END = 300
REWARD_END = 390


def _common_setup(context, props) -> None:
    """模板公共前置：工程、片长、默认分镜。"""
    scene_lib.new_project(context, props)
    props.duration = 15.0
    scene_lib.apply_size(context, props)
    shot_lib.setup_default(context)


def _select(objects) -> None:
    util.select_only(bpy.context, list(objects))


def _apply_mat(objects, key: str, color=(1.0, 1.0, 1.0)) -> None:
    _select(objects)
    material_lib.apply_to_selection(bpy.context, key, color)


def _finish_template(context, template_key: str) -> None:
    """模板收尾：结尾卡 + 卡点标记 + 回到主场景。"""
    props = context.scene.uastudio
    props.endcard_template = {
        "drop": "center", "screw": "banner", "level": "splash",
        "doors": "center", "sort": "banner", "jenga": "center",
    }.get(template_key, "center")
    scene = context.scene  # make_endcard 会切活动场景，先抓主场景引用
    endcard_lib.make_endcard(
        context, props.endcard_template,
        props.logo_path, props.app_name, props.cta_text,
    )
    for fr in (HOOK_END, PLAY_MID, PLAY_END, REWARD_END):
        anim_lib.add_beat(scene, frame=fr)
    try:
        context.window.scene = scene
    except (AttributeError, RuntimeError):
        pass


# ---------------------------------------------------------------------------
# 模板 1：掉落消除（金币掉落 → 手指点击 → 收集飞入 → 爽点）
# ---------------------------------------------------------------------------


def build_drop(context) -> int:
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "podium"
    props.light_mode = "three_point"
    _common_setup(context, props)
    scene = context.scene

    # 素材：6 金币 + 1 宝石
    coins = []
    for i in range(6):
        c = asset_lib.add_shape(context, "coin")
        c.location = (-1.5 + i * 0.6, -0.4 + (i % 2) * 0.8, 0.67)
        coins.append(c)
    gem = asset_lib.add_shape(context, "gem")
    gem.location = (0.7, 0.9, 0.45)
    _apply_mat(coins, "gold")
    _apply_mat([gem], "candy", (0.35, 0.75, 1.0))

    # Hook（帧 1-90）：金币坠落弹跳 + 相机推近
    scene.frame_set(1)
    _select(coins + [gem])
    anim_lib.entrance(context, "drop", gap=0.08)
    anim_lib.camera_move(context, "push_in", 3.0)

    # 玩法（90-210）：手指点击 + 收集飞入 + 卡点震屏
    scene.frame_set(90)
    _select([coins[2]])
    game_fx_lib.hand_tap(context, 1.0)
    scene.frame_set(120)
    _select(coins[0:3])
    game_fx_lib.fx_vanish(context, 0.5, to_corner=True)
    scene.frame_set(120)
    anim_lib.camera_move(context, "shake", 0.4)

    # 爽点（210-390）：飞分 + 彩带 + 星尘 + 环绕展示
    scene.frame_set(215)
    _select([gem])
    game_fx_lib.fx_score_text(context, "+100", 0.9)
    physics_lib.fx_particle(context, "confetti", 60, start_frame=240)
    physics_lib.fx_particle(context, "stardust", 40, start_frame=300)
    scene.frame_set(300)
    anim_lib.camera_move(context, "orbit", 3.0)

    # HUD
    game_fx_lib.make_hud_score(context, "分数 0")
    game_fx_lib.make_hud_progress(context, 0.6)

    _finish_template(context, "drop")
    scene.frame_set(1)
    return 8


# ---------------------------------------------------------------------------
# 模板 2：螺丝拧拧（桌面四颗螺丝逐个拧出）
# ---------------------------------------------------------------------------


def build_screw(context) -> int:
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "desk"
    props.light_mode = "softbox"
    props.bg_mode = "studio"
    _common_setup(context, props)
    scene = context.scene

    # 素材：4 颗螺丝排在桌面
    screws = []
    for i in range(4):
        s = asset_lib.add_shape(context, "screw")
        s.location = (-0.9 + i * 0.6, 0, 0.7)
        screws.append(s)
    _apply_mat(screws, "silver")

    # Hook：推近 + 首颗螺丝手指点击
    scene.frame_set(1)
    anim_lib.camera_move(context, "push_in", 3.0)
    scene.frame_set(45)
    _select([screws[0]])
    game_fx_lib.hand_tap(context, 1.0)

    # 玩法：逐颗拧出（旋转飞出 + 缩小消失，错帧）
    for i, s in enumerate(screws):
        st_scale = tuple(s.scale)
        st_rot = tuple(s.rotation_euler)
        start = 90 + i * round(0.8 * anim_lib._f())
        anim_lib._kf(s, "rotation_euler",
                     [st_rot,
                      (st_rot[0], st_rot[1], st_rot[2] + math.tau * 2),
                      (st_rot[0], st_rot[1], st_rot[2] + math.tau * 2)],
                     [start, start + round(0.6 * anim_lib._f()), start + round(1.0 * anim_lib._f())],
                     interp="EXPO")
        anim_lib._kf(s, "scale",
                     [st_scale, st_scale, (0.001,) * 3],
                     [start, start + round(0.6 * anim_lib._f()), start + round(1.0 * anim_lib._f())],
                     interp="SINE")

    # HUD + 收尾彩带
    game_fx_lib.make_hud_progress(context, 0.75)
    physics_lib.fx_particle(context, "confetti", 50, start_frame=270)

    _finish_template(context, "screw")
    scene.frame_set(1)
    return 6


# ---------------------------------------------------------------------------
# 模板 3：我要通关（宝石矩阵逐个点亮 + 全屏爽点）
# ---------------------------------------------------------------------------


def build_level(context) -> int:
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "podium"
    props.light_mode = "sky"
    _common_setup(context, props)
    scene = context.scene

    # 素材：9 宝石 3x3 矩阵（缩小到 0.5），三色糖果材质
    gems = []
    for i in range(3):
        for j in range(3):
            g = asset_lib.add_shape(context, "gem")
            g.scale = (0.5, 0.5, 0.5)
            g.location = (-0.9 + i * 0.9, -0.45 + j * 0.7, 0.4)
            gems.append(g)
    palette = [(0.9, 0.3, 0.3), (0.3, 0.7, 1.0), (0.35, 0.9, 0.45)]
    for idx, g in enumerate(gems):
        _apply_mat([g], "candy", palette[idx % 3])

    # Hook：宝石波浪 pop 入场 + 环绕运镜
    scene.frame_set(1)
    _select(gems)
    anim_lib.entrance(context, "pop", gap=0.06)
    anim_lib.camera_move(context, "orbit", 5.0)

    # 爽点：逐个消除 + 三连飞分
    scene.frame_set(240)
    _select(gems[0:3])
    game_fx_lib.fx_vanish(context, 0.45, to_corner=False)
    scene.frame_set(260)
    _select([gems[4]])
    game_fx_lib.fx_score_text(context, "+300", 1.0)
    scene.frame_set(285)
    _select(gems[3:7])
    game_fx_lib.fx_vanish(context, 0.45, to_corner=False)

    # 奖励：彩带 + 星尘 + 金币喷泉
    physics_lib.fx_particle(context, "confetti", 80, start_frame=300)
    physics_lib.fx_particle(context, "coins", 50, start_frame=330)
    physics_lib.fx_particle(context, "stardust", 40, start_frame=360)

    game_fx_lib.make_hud_score(context, "分数 980")
    game_fx_lib.make_hud_progress(context, 0.85)

    _finish_template(context, "level")
    scene.frame_set(1)
    return 13


# ---------------------------------------------------------------------------
# 模板 4：数字门逃生（两扇门 + 数学题，选对门奖励 / 选错门翻车）
# ---------------------------------------------------------------------------


def build_doors(context) -> int:
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "floor"
    props.light_mode = "softbox"
    props.bg_mode = "flat"
    _common_setup(context, props)
    scene = context.scene

    # 两扇门：红(错) 蓝(对)，门 = 大圆角方块 + 数字牌
    doors = []
    for i, (color_key, xpos) in enumerate((("fire", -1.4), ("cool", 1.4))):
        bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD",
                                        location=(xpos, 0.4, 1.5))
        door = context.active_object
        door.scale = (1.3, 0.18, 2.8)
        _apply_mat([door], "candy",
                   (0.9, 0.25, 0.2) if i == 0 else (0.2, 0.45, 0.95))
        door.name = "UA_Door_" + ("Wrong" if i == 0 else "Right")
        doors.append(door)
        # 数字牌：门面中央文本（2+2=? / 1+1=?）
        curve = bpy.data.curves.new("UA_DoorNum" + str(i), type="FONT")
        curve.body = ("1+1" if i == 1 else "2+2") + "=?"
        curve.size = 0.5
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.extrude = 0.02
        num = bpy.data.objects.new("UA_DoorNum" + str(i), curve)
        num.location = (xpos, 0.1, 1.9)
        num.data.materials.append(
            endcard_lib._plane_mat("UA_DoorNum_Mat", (1, 1, 1),
                                   emissive=True))
        scene.collection.objects.link(num)
        coll = util.ensure_collection(context, "UA_Objects")
        util.move_to_collection(num, coll)

    # 门框地面引导条
    _ = doors

    # Hook：推近数字题
    scene.frame_set(1)
    anim_lib.camera_move(context, "push_in", 3.0)

    # 玩法：手指点对门（蓝色）→ 对门发光弹跳 / 错门缩小消失
    scene.frame_set(110)
    _select([doors[1]])
    game_fx_lib.hand_tap(context, 1.2)
    scene.frame_set(150)
    _select([doors[1]])
    game_fx_lib.fx_score_text(context, "✔ 通关!", 1.0)
    scene.frame_set(180)
    _select([doors[0]])
    game_fx_lib.fx_vanish(context, 0.5, to_corner=False)

    # 奖励：金币喷泉 + 彩带 + 星尘
    physics_lib.fx_particle(context, "coins", 60, start_frame=240)
    physics_lib.fx_particle(context, "confetti", 70, start_frame=270)
    physics_lib.fx_particle(context, "stardust", 40, start_frame=320)
    scene.frame_set(280)
    anim_lib.camera_move(context, "shake", 0.4)

    game_fx_lib.make_hud_score(context, "分数 500")
    game_fx_lib.make_hud_progress(context, 0.5)

    _finish_template(context, "doors")
    scene.frame_set(1)
    return 10


def build_sort(context) -> int:
    """颜色排序模板：四色杯逐个点击收集（超休闲经典品类）。"""
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "podium"
    props.light_mode = "three_point"
    _common_setup(context, props)
    scene = context.scene

    # 四个杯子（圆柱容器）+ 每杯两颗彩球
    ball_colors = {
        "red": (0.9, 0.2, 0.2), "green": (0.3, 0.85, 0.4),
        "blue": (0.25, 0.55, 1.0), "yellow": (1.0, 0.85, 0.2),
    }
    cups = []
    for i in range(4):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.45, depth=0.9, vertices=48, align="WORLD",
            location=(-1.35 + i * 0.9, 0, 0.82),
        )
        cup = context.active_object
        cup.name = "UA_Cup_" + str(i)
        _apply_mat([cup], "silver")
        cups.append(cup)

    balls = []
    palette_keys = list(ball_colors)
    for ci in range(4):
        for bi in range(2):
            key = palette_keys[(ci + bi) % 4]
            mat_name = "UA_Ball_" + key
            mat = bpy.data.materials.get(mat_name)
            if mat is None:
                mat = bpy.data.materials.new(mat_name)
            material_lib.MATS["candy"][1](mat, ball_colors[key])
            z = 0.55 + bi * 0.5
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.28, segments=32, ring_count=16, align="WORLD",
                location=(-1.35 + ci * 0.9, 0, z),
            )
            ball = context.active_object
            ball.name = "UA_SortBall_%d_%d" % (ci, bi)
            ball.data.materials.append(mat)
            balls.append(ball)
            util.move_to_collection(
                ball, util.ensure_collection(context, "UA_Objects"))

    # Hook：杯子 pop 入场 + 定制高角度俯视机位（排序品类需俯看杯内）
    scene.frame_set(1)
    _select(cups)
    anim_lib.entrance(context, "pop", gap=0.06)
    cam = util.find_object("UA_Camera")
    if cam is not None:
        cam.location = (0.0, -4.0, 6.5)
        util.look_at(cam, (0.0, 0.0, 0.2))
    # 排序品类经典视角：固定高角度俯视（不 orbit，杯内球始终可见）

    # 玩法：逐杯点击顶层球 → 收集飞入（每 45 帧一组）
    for i in range(4):
        base_frame = 90 + i * 45
        top = bpy.data.objects.get("UA_SortBall_%d_1" % i)
        if top is None:
            continue
        scene.frame_set(base_frame)
        _select([top])
        game_fx_lib.hand_tap(context, 1.0)
        scene.frame_set(base_frame + 10)
        _select([top])
        game_fx_lib.fx_vanish(context, 0.4, to_corner=True)

    # 爽点：彩带 + 星尘 + 震屏
    scene.frame_set(280)
    physics_lib.fx_particle(context, "confetti", 60, start_frame=280)
    physics_lib.fx_particle(context, "stardust", 40, start_frame=320)
    scene.frame_set(300)
    anim_lib.camera_move(context, "shake", 0.4)

    game_fx_lib.make_hud_score(context, "分数 640")
    game_fx_lib.make_hud_progress(context, 0.7)

    _finish_template(context, "sort")
    scene.frame_set(1)
    return 12


# ---------------------------------------------------------------------------
# 模板 6：叠叠乐（抽块 → 倒塌物理，惊险感品类）
# ---------------------------------------------------------------------------


def build_jenga(context) -> int:
    props = context.scene.uastudio
    props.engine = "eevee"
    props.stage = "floor"
    props.light_mode = "softbox"
    props.bg_mode = "studio"
    _common_setup(context, props)
    scene = context.scene

    # 塔：12 层 × 3 块交替方向（块 0.7×0.24×0.16，木纹）
    blocks = []
    bw, bl, bh = 0.24, 0.72, 0.16
    for li in range(12):
        z = 0.08 + li * bh
        angle = (li % 2) * math.pi / 2
        for bi in range(3):
            off = (bi - 1) * bw
            if li % 2 == 0:
                loc = (off, 0, z)
            else:
                loc = (0, off, z)
            bpy.ops.mesh.primitive_cube_add(size=1, align="WORLD",
                                            location=loc)
            blk = context.active_object
            blk.rotation_euler = (0, 0, angle)
            blk.scale = (bl if li % 2 == 0 else bw,
                         bw if li % 2 == 0 else bl, bh)
            blk.name = "UA_Jenga_%02d_%d" % (li, bi)
            _apply_mat([blk], "wood")
            blocks.append(blk)

    # 地板被动碰撞体（倒塌垫底）
    scene.frame_set(1)
    physics_lib.set_stage_passive(context)

    # 全部块：主动刚体 + kinematic 逐键（True → collapse 帧切 False）
    physics_lib.add_rigid(context, blocks, "ACTIVE")
    collapse_frame = 210
    for blk in blocks:
        blk.rigid_body.kinematic = True
        blk.keyframe_insert(data_path="rigid_body.kinematic",
                            frame=scene.frame_start)
        blk.rigid_body.kinematic = False
        blk.keyframe_insert(data_path="rigid_body.kinematic",
                            frame=collapse_frame)
        blk.rigid_body.kinematic = True  # 恢复属性（实际值由 fcurve 驱动）

    # Hook：推近
    anim_lib.camera_move(context, "push_in", 3.0)

    # 玩法：手指点中层中块 → 缓慢抽块（kinematic K 帧滑出）
    scene.frame_set(90)
    _select([blocks[7 * 3 + 1]])
    game_fx_lib.hand_tap(context, 1.0)

    slide = blocks[7 * 3 + 1]
    slide_axis = (0, 1.4, 0) if 7 % 2 == 1 else (1.4, 0, 0)
    st_loc = tuple(slide.location)
    f = anim_lib._f()
    pull_start = 120
    pull_end = pull_start + round(1.6 * f)
    anim_lib._kf(slide, "location",
                 [st_loc,
                  (st_loc[0] + slide_axis[0] * 0.5,
                   st_loc[1] + slide_axis[1] * 0.5,
                   st_loc[2]),
                  (st_loc[0] + slide_axis[0] * 1.4,
                   st_loc[1] + slide_axis[1] * 1.4,
                   st_loc[2])],
                 [pull_start, pull_start + round(0.8 * f), pull_end],
                 interp="SINE")

    # collapse 帧后 kinematic F 曲线切 False → 自然倒塌（惊险感核心）

    # 爽点：倒塌后彩带 + 星尘 + 震屏
    physics_lib.fx_particle(context, "confetti", 60, start_frame=collapse_frame + 20)
    physics_lib.fx_particle(context, "stardust", 40, start_frame=collapse_frame + 40)
    scene.frame_set(collapse_frame + 30)
    anim_lib.camera_move(context, "shake", 0.4)

    game_fx_lib.make_hud_score(context, "分数 900")
    game_fx_lib.make_hud_progress(context, 0.8)

    physics_lib.bake_all(context)
    _finish_template(context, "screw")
    scene.frame_set(1)
    return 13


TEMPLATES = {
    "drop": ("掉落消除", build_drop),
    "screw": ("螺丝拧拧", build_screw),
    "jenga": ("叠叠乐倒塌", build_jenga),
    "level": ("我要通关", build_level),
    "doors": ("数字门逃生", build_doors),
    "sort": ("颜色排序", build_sort),
}


def build_template(context, key: str) -> int:
    entry = TEMPLATES.get(key)
    if entry is None:
        raise ValueError("未知模板 " + key)
    return entry[1](context)
