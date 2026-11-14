#!/bin/bash
# 买量工坊 UA Studio · macOS 双击安装脚本
# 双击运行：构建 zip → 安装到 Blender user_default → 启用
set -e

BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
SRC="$(cd "$(dirname "$0")" && pwd)"
ZIP="$SRC/dist/ua_studio-0.1.0.zip"

if [ ! -f "$ZIP" ]; then
    "$BLENDER" --command extension build --source-dir "$SRC" --output-dir "$SRC/dist"
fi

"$BLENDER" -b --command extension install-file -r user_default -e "$ZIP"

echo ""
echo "✅ 买量工坊安装完成。重启 Blender，在 3D 视口按 N 打开「买量工坊」面板。"
echo ""
read -n 1 -s -r -p "按任意键关闭..."
