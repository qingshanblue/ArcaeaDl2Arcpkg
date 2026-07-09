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

echo "0b. 解压 in/songs.zip (必需)"
if [ -f "./in/songs.zip" ]; then
    if [ -d "./tmp/songs" ]; then
        if ask "检测到 tmp/songs/ 已存在，是否覆盖解压？"; then
            step "解压 in/songs.zip (覆盖)" bash -c 'pv ./in/songs.zip | bsdtar -xf - -C tmp'
        else
            warn "跳过解压，使用现有 tmp/songs/"
        fi
    else
        step "解压 in/songs.zip" bash -c 'pv ./in/songs.zip | bsdtar -xf - -C tmp'
    fi
else
    err "未找到 in/songs.zip（必需输入），无法继续"
    exit 1
fi

echo "1. 整理 tmp/dl/ 中，按不同歌曲分为不同文件夹"
step "整理 tmp/dl/ 为 tmp/charts/" pixi run python utils/arcaea_charts_sort.py --dl-dir tmp/dl --charts-dir tmp/charts

echo "1b. 合并 tmp/songs/ 中的免费歌曲与 dl_ 额外信息到 tmp/charts/"
step "合并 songs 到 charts" pixi run python utils/merge_songs.py --songs-dir tmp/songs --charts-dir tmp/charts

# echo "2. 将etr转换为byd，ARCcreate不支持读取ETR"
# pixi run python utils/etr2byd.py tmp/charts

echo "3. 生成 arcproj，才可被 ARCcreate 读取"
step "生成 project.arcproj" pixi run python utils/generate_arcproj.py -i tmp/charts --bpm-yaml in/bpmSpecialCasesList.yaml --songlist tmp/songs/songlist

echo "4. 按 set 拆分歌曲为多个曲包（追加章节 alice_append_1 等归入基础包 alice；songlist 有但 packlist 无的 set 如 single 按其自身为名成包并用 1080_select_<set>.png；仅完全不在 songlist 的歌进兜底包 qings.Extra；生成 pack.yml/index.yml 并放置封面）"
step "拆分并生成多曲包" pixi run python utils/split_packs.py --charts-dir tmp/charts --songlist tmp/songs/songlist --packlist tmp/songs/packlist --songs-dir tmp/songs --publisher qings

echo "5. 将每个曲包分别压缩为 out/qings.<真实名>.arcpkg（文件夹名即真实名，空格已转下划线）"
mkdir -p out
if [ -d "./tmp/packs" ]; then
    for d in tmp/packs/*/; do
        [ -d "$d" ] || continue
        base="$(basename "$d")"
        if [ -f "./out/${base}.arcpkg" ]; then
            warn "out/${base}.arcpkg 已存在，跳过"
            continue
        fi
        step "压缩 ${base} 为 out/${base}.arcpkg" bash -c "cd '$d' && zip -rq - . | pv -s \"\$(du -sb . | awk '{print \$1}')\" > \"\$(pwd)/../../../out/${base}.zip\" && mv \"\$(pwd)/../../../out/${base}.zip\" \"\$(pwd)/../../../out/${base}.arcpkg\""
    done
else
    err "tmp/packs/ 不存在，无法压缩"
    exit 1
fi

ok "全部转换完成，产物位于 out/qings.<真实名>.arcpkg（每个官方 set 一个，外加兜底 qings.Extra）"
