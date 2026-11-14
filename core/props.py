"""面板属性组：所有「一键」参数集中挂在 Scene.uastudio。"""

from __future__ import annotations

import bpy

from . import util


class UAShot(bpy.types.PropertyGroup):
    """一个分镜条目：名称 + 帧区间。"""

    name: bpy.props.StringProperty(name="分镜名")
    start: bpy.props.IntProperty(name="起始帧", min=1)
    end: bpy.props.IntProperty(name="结束帧", min=1)


class UAProperties(bpy.types.PropertyGroup):
    """买量工坊全局设置（面板直接绑定读写）。"""

    # ① 工程
    aspect: bpy.props.EnumProperty(
        name="画幅",
        items=[
            ("9:16", "竖屏 9:16", "1080 x 1920"),
            ("1:1", "方形 1:1", "1080 x 1080"),
            ("16:9", "横屏 16:9", "1920 x 1080"),
        ],
        default="9:16",
    )
    fps: bpy.props.IntProperty(name="帧率", default=30, min=24, max=60)
    duration: bpy.props.FloatProperty(
        name="片长(秒)", default=15.0, min=3.0, max=120.0
    )
    engine: bpy.props.EnumProperty(
        name="引擎",
        items=[
            ("eevee", "EEVEE 快速", "EEVEE 实时渲染，出片快"),
            ("cycles", "Cycles 高质", "路径追踪，质量更高"),
        ],
        default="eevee",
    )

    # 背景
    bg_mode: bpy.props.EnumProperty(
        name="背景",
        items=[
            ("gradient", "双色渐变", "上深下浅程序化渐变"),
            ("flat", "纯色", "单色背景"),
            ("studio", "影棚", "中性灰影棚背景"),
        ],
        default="gradient",
    )
    bg_top: bpy.props.FloatVectorProperty(
        name="顶部色", subtype="COLOR", size=3, min=0.0, max=1.0,
        default=(0.02, 0.04, 0.11),
    )
    bg_bottom: bpy.props.FloatVectorProperty(
        name="底部色", subtype="COLOR", size=3, min=0.0, max=1.0,
        default=(0.25, 0.55, 0.95),
    )

    # 舞台
    stage: bpy.props.EnumProperty(
        name="舞台",
        items=[
            ("podium", "圆形展台", "广告常用圆形展台"),
            ("desk", "桌面", "水平桌面（适合俯视展示）"),
            ("floor", "无限地面", "大平面地面"),
            ("none", "无舞台", "不建舞台"),
        ],
        default="podium",
    )

    # 灯光
    light_mode: bpy.props.EnumProperty(
        name="布光",
        items=[
            ("three_point", "三点布光", "主光/补光/轮廓光"),
            ("softbox", "柔光箱", "大柔光+两侧补"),
            ("sky", "天空光", "程序化天空环境光"),
            ("none", "无灯光", "不建灯"),
        ],
        default="three_point",
    )
    light_strength: bpy.props.FloatProperty(
        name="灯光强度", default=1.0, min=0.1, max=5.0, soft_max=3.0
    )

    # ② 资产
    scatter_count: bpy.props.IntProperty(
        name="散布数量", default=8, min=1, max=50
    )
    scatter_radius: bpy.props.FloatProperty(
        name="散布半径", default=3.0, min=0.5, max=8.0
    )
    scatter_seed: bpy.props.IntProperty(name="随机种子", default=0)

    grid_cols: bpy.props.IntProperty(name="列数", default=4, min=1, max=20)
    grid_rows: bpy.props.IntProperty(name="行数", default=3, min=1, max=20)
    grid_spacing: bpy.props.FloatProperty(
        name="间距", default=1.2, min=0.5, max=5.0
    )

    ring_count: bpy.props.IntProperty(name="数量", default=8, min=1, max=36)
    ring_radius: bpy.props.FloatProperty(
        name="环半径", default=2.0, min=0.5, max=8.0
    )

    text_body: bpy.props.StringProperty(name="文字内容", default="限时挑战")
    text_size: bpy.props.FloatProperty(
        name="字号", default=0.8, min=0.1, max=3.0
    )
    text_extrude: bpy.props.FloatProperty(
        name="厚度", default=0.05, min=0.0, max=0.3
    )

    # ③ 材质
    mat_color: bpy.props.FloatVectorProperty(
        name="主色", subtype="COLOR", size=3, min=0.0, max=1.0,
        default=(0.85, 0.2, 0.25),
    )

    # ④ 动画
    entrance_gap: bpy.props.FloatProperty(
        name="错帧间隔(秒)", default=0.15, min=0.0, max=2.0
    )

    # ⑥ 相机
    cam_seconds: bpy.props.FloatProperty(
        name="运镜时长(秒)", default=3.0, min=0.5, max=15.0
    )

    # ⑤ 物理
    fracture_count: bpy.props.IntProperty(
        name="碎片数量", default=30, min=5, max=300
    )
    fracture_noise: bpy.props.FloatProperty(
        name="碎片随机度", default=1.0, min=0.0, max=3.0
    )
    fracture_explode: bpy.props.BoolProperty(
        name="自动炸开", default=True,
        description="破碎后自动加爆开力场",
    )
    explode_strength: bpy.props.FloatProperty(
        name="爆开强度", default=6.0, min=0.0, max=30.0
    )
    fx_count: bpy.props.IntProperty(
        name="粒子数量", default=80, min=10, max=500
    )
    fluid_resolution: bpy.props.IntProperty(
        name="流体分辨率", default=48, min=16, max=256
    )

    # ⑦ 渲染
    out_format: bpy.props.EnumProperty(
        name="输出格式",
        items=[
            ("mp4", "MP4 成片", "H.264 竖屏成片，直接可投放"),
            ("png_seq", "PNG 透明序列", "带透明通道序列帧，后期合成用"),
        ],
        default="mp4",
    )
    out_dir: bpy.props.StringProperty(
        name="输出目录", default="//renders", subtype="FILE_PATH"
    )
    transparent: bpy.props.BoolProperty(
        name="透明背景", default=False,
        description="PNG 序列自动透明；MP4 建议关闭",
    )

    # ⑧ 结尾卡
    endcard_template: bpy.props.EnumProperty(
        name="模板",
        items=[
            ("center", "居中卡片", "白卡片+logo+按钮"),
            ("banner", "底部横条", "不遮挡主体"),
            ("splash", "全屏大图", "彩底大 logo 冲击力强"),
        ],
        default="center",
    )
    logo_path: bpy.props.StringProperty(name="logo 路径", default="")
    app_name: bpy.props.StringProperty(name="应用名", default="限时挑战")
    cta_text: bpy.props.StringProperty(name="按钮文案", default="立即下载")
    endcard_animate: bpy.props.BoolProperty(name="入场动画", default=True)

    # 🎮 假玩法
    hand_scale: bpy.props.FloatProperty(
        name="手指大小", default=1.0, min=0.4, max=3.0
    )
    fx_vanish_sec: bpy.props.FloatProperty(
        name="消除时长(秒)", default=0.5, min=0.2, max=2.0
    )
    fx_text_body: bpy.props.StringProperty(name="飞分文字", default="+100")
    hud_score_body: bpy.props.StringProperty(name="分数文案", default="分数 1280")
    hud_ratio: bpy.props.FloatProperty(
        name="进度比例", default=0.62, min=0.0, max=1.0
    )
    cover_frame: bpy.props.IntProperty(
        name="封面帧", default=1, min=1, max=99999
    )

    # ✨ 画质与风格
    quality_level: bpy.props.EnumProperty(
        name="质量档位",
        items=[
            ("draft", "草稿", "EEVEE 16 采样，快速预览"),
            ("standard", "标准", "EEVEE 64 采样+光追"),
            ("high", "高质", "EEVEE 256 采样+光追+运动模糊"),
            ("film", "电影", "Cycles 256 采样+降噪"),
        ],
        default="standard",
    )
    bloom_on: bpy.props.BoolProperty(
        name="辉光 Bloom(实验性)", default=False,
        description="5.1.2 构建的合成器节点组求值有崩溃风险，默认关闭")
    bloom_strength: bpy.props.FloatProperty(
        name="辉光强度", default=0.5, min=0.0, max=1.0
    )
    vignette_on: bpy.props.BoolProperty(
        name="晕影(实验性)", default=False,
        description="同上，默认关闭")
    color_style: bpy.props.EnumProperty(
        name="色彩风格",
        items=[
            ("bright", "明快", "提亮，糖果感"),
            ("rich", "浓郁", "压暗高对比"),
            ("cool", "清冷", "中性偏冷"),
            ("warm", "暖调", "轻微提亮偏暖"),
        ],
        default="bright",
    )
    dof_fstop: bpy.props.FloatProperty(
        name="光圈 f 值", default=2.8, min=1.0, max=16.0
    )

    # 🎬 分镜
    shots: bpy.props.CollectionProperty(type=UAShot)
    bgm_path: bpy.props.StringProperty(name="BGM 路径", default="")
    beat_sensitivity: bpy.props.FloatProperty(
        name="节拍灵敏度", default=1.4, min=0.4, max=3.0,
        description="越低卡点越多",
    )

    # 🎨 贴纸
    sticker_symbol: bpy.props.StringProperty(name="贴纸内容", default="★")
    sticker_palette: bpy.props.EnumProperty(
        name="配色",
        items=[
            ("gold", "金色", "星星/奖励"),
            ("fire", "火焰", "爽点/连击"),
            ("cool", "冰蓝", "技能/道具"),
            ("mint", "薄荷", "通过/成功"),
        ],
        default="gold",
    )


def register() -> None:
    bpy.utils.register_class(UAShot)
    bpy.utils.register_class(UAProperties)
    bpy.types.Scene.uastudio = bpy.props.PointerProperty(type=UAProperties)


def unregister() -> None:
    del bpy.types.Scene.uastudio
    bpy.utils.unregister_class(UAProperties)
    bpy.utils.unregister_class(UAShot)
