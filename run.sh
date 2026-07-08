#!/usr/bin/env bash
set -uo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ [成功] $*${NC}"; }
err()  { echo -e "${RED}❌ [错误] $*${NC}" >&2; }
warn() { echo -e "${YELLOW}⚠️  [警告] $*${NC}"; }

# 执行命令：成功打印 ✅，失败打印 ❌ 并中止脚本
step() {
    local msg="$1"; shift
    if "$@"; then
        ok "$msg"
    else
        err "执行失败: $msg (命令: $*)"
        exit 1
    fi
}

# 询问 y/N，默认否；返回 0=是, 1=否
ask() {
    local ans
    read -r -p "$1 [y/N] " ans
    case "$ans" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

echo "===== 开始转换 Arcaea 谱面为 .arcpkg ====="

echo "0. 解压 in/dl.zip"
mkdir -p tmp
if [ -f "./in/dl.zip" ]; then
    if [ -d "./tmp/dl" ]; then
        if ask "检测到 tmp/dl/ 已存在，是否覆盖解压？"; then
            step "解压 in/dl.zip (覆盖)" bash -c 'pv ./in/dl.zip | bsdtar -xf - -C tmp'
        else
            warn "跳过解压，使用现有 tmp/dl/"
        fi
    else
        step "解压 in/dl.zip" bash -c 'pv ./in/dl.zip | bsdtar -xf - -C tmp'
    fi
else
    if [ -d "./tmp/dl" ]; then
        if ask "未找到 in/dl.zip，但 tmp/dl/ 已存在，是否跳过解压继续使用？"; then
            warn "跳过解压，使用现有 tmp/dl/"
        else
            err "未找到 in/dl.zip 且选择不解压，无法继续"
            exit 1
        fi
    else
        err "未找到 in/dl.zip 且 tmp/dl/ 不存在，无法继续"
        exit 1
    fi
fi

echo "1. 整理 tmp/dl/ 中，按不同歌曲分为不同文件夹"
step "整理 tmp/dl/ 为 tmp/charts/" pixi run python utils/arcaea_charts_sort.py --dl-dir tmp/dl --charts-dir tmp/charts

# echo "2. 将etr转换为byd，ARCcreate不支持读取ETR"
# pixi run python utils/etr2byd.py tmp/charts

echo "3. 生成 arcproj，才可被 ARCcreate 读取"
step "生成 project.arcproj" pixi run python utils/generate_arcproj.py -i tmp/charts --bpm-yaml in/bpmSpecialCasesList.yaml

echo "4. 生成 yml，组织所有歌曲为曲包方便使用"
step "生成 pack.yml 与 index.yml" pixi run python utils/generate_yml.py -i tmp/charts

echo "5. 复制图片 in/pack.png (314x756) 到曲包文件夹"
if [ -f "./tmp/charts/qings/pack.png" ]; then
    warn "pack.png 已存在，跳过复制"
else
    step "复制 pack.png" cp ./in/pack.png ./tmp/charts/qings/pack.png
fi

echo "6. 压缩 ./tmp/charts/ 下的所有文件为 zip 并命名为 qings.zip"
mkdir -p out
if [ -f "./out/qings.zip" ] || [ -f "./out/qings.arcpkg" ]; then
    warn "out/qings.zip 或 out/qings.arcpkg 已存在，跳过压缩"
else
    step "压缩 tmp/charts/ 为 out/qings.zip" bash -c 'cd tmp/charts && zip -rq - . | pv -s "$(du -sb . | awk "{print \$1}")" > ../../out/qings.zip'
fi

echo "7. 重命名 out/qings.zip 为 out/qings.arcpkg"
if [ -f "./out/qings.arcpkg" ]; then
    warn "out/qings.arcpkg 已存在，跳过重命名"
else
    step "重命名为 out/qings.arcpkg" mv out/qings.zip out/qings.arcpkg
fi

ok "全部转换完成，产物位于 out/qings.arcpkg"
