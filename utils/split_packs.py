import os
import re
import sys
import json
import glob
import shutil
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_yml import generate_pack_files


def load_songlist_set_map(path):
    """读取 songlist，返回 {id: set}（set 缺失则为 None）。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    result = {}
    for song in data.get("songs", []):
        sid = song.get("id")
        if not sid:
            continue
        result[sid] = song.get("set")
    return result


def load_packlist_names(path):
    """读取 packlist，返回 {id: name_localized(dict)}。兼容 JSON 数组或含列表字段的对象。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                items = v
                break

    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        iid = item.get("id")
        if not iid:
            continue
        result[iid] = item.get("name_localized")
    return result


def localized_name(value):
    """name_localized 取值：优先 en，否则首个值。"""
    if isinstance(value, dict):
        if "en" in value and value["en"]:
            return str(value["en"])
        for v in value.values():
            if v:
                return str(v)
    return None


def sanitize(name):
    """转为安全的内部包文件夹名（ASCII）：空白转下划线，去除首尾空格，仅保留安全字符。"""
    s = str(name).strip().replace(" ", "_")
    s = re.sub(r"[^0-9A-Za-z_.\\-]+", "", s)
    return s or "unknown"


def safe_filename(name):
    """转为安全文件名（保留 Unicode/中文）：空格转下划线，剔除路径非法字符，去首尾空格/点。"""
    s = str(name).strip().replace(" ", "_")
    s = re.sub(r'[\\/:*?"<>|]', "", s)
    s = s.strip().strip(".")
    return s or "unknown"


def canonical_set(raw):
    """去掉末尾的 _append_<数字> 段，使追加章节并入基础包（如 alice_append_1 -> alice）。"""
    return re.sub(r"_append_\d+$", "", str(raw))


def find_pack_image(songs_dir, set_raw, set_key):
    """在 songs/pack/ 下查找 1080_select_<set>.png（大小写不敏感），返回路径或 None。"""
    pack_dir = os.path.join(songs_dir, "pack")
    if not os.path.isdir(pack_dir):
        return None
    for cand in (set_raw, set_key):
        if not cand:
            continue
        target = f"1080_select_{cand}.png".lower()
        for entry in os.listdir(pack_dir):
            if entry.lower() == target:
                return os.path.join(pack_dir, entry)
    return None


def split_packs(
    charts_dir="tmp/charts",
    songlist_path="tmp/songs/songlist",
    packlist_path="tmp/songs/packlist",
    songs_dir="tmp/songs",
    packs_dir="tmp/packs",
    publisher="qings",
    fallback_image="in/pack.png",
):
    charts_path = os.path.join(charts_dir)
    if not os.path.isdir(charts_path):
        print(f"错误: 文件夹 '{charts_dir}' 不存在！请先生成 project.arcproj。")
        return

    songlist_map = load_songlist_set_map(songlist_path)
    packlist_names = load_packlist_names(packlist_path)

    # 清空并按 set 重组到 tmp/packs/
    if os.path.isdir(packs_dir):
        shutil.rmtree(packs_dir)
    os.makedirs(packs_dir, exist_ok=True)

    # 兜底包：所有 set 不在 packlist / 缺失 set 的歌曲统一收进这里
    CATCHALL_KEY = f"{publisher}.Extra"
    CATCHALL_DISPLAY = "Extra"

    # packkey -> {"display": 显示名, "sets": [set_raw...], "is_catchall": bool}
    packs = {}

    print("开始按 set 拆分歌曲文件夹...")
    copied = 0
    for entry in sorted(os.listdir(charts_path)):
        src = os.path.join(charts_path, entry)
        if not os.path.isdir(src):
            continue
        if not os.path.isfile(os.path.join(src, "project.arcproj")):
            continue

        raw = songlist_map.get(entry)
        in_songlist = raw is not None
        set_raw = raw if raw else "unknown"

        # 规范化 set：去掉末尾 _append_<数字>，使追加章节并入基础包（alice_append_1 -> alice）
        canonical = canonical_set(set_raw)

        # 判定归属：
        #  1) 规范化后的 set 在 packlist 中 -> 官方包（显示名取 packlist）
        #  2) 歌曲本身在 songlist 但 packlist 无此包（如 single）-> 以 set 自身为名成包
        #  3) 完全不在 songlist（查不到 set）-> 兜底包 qings.Extra
        if canonical in packlist_names:
            display = localized_name(packlist_names.get(canonical)) or canonical
            is_catchall = False
        elif in_songlist:
            display = canonical
            is_catchall = False
        else:
            display = CATCHALL_DISPLAY
            is_catchall = True

        packkey = CATCHALL_KEY if is_catchall else f"{publisher}.{safe_filename(display)}"

        packs.setdefault(packkey, {"display": display, "canonical": canonical, "sets": [], "is_catchall": is_catchall})
        packs[packkey]["sets"].append(set_raw)

        dest = os.path.join(packs_dir, packkey, entry)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        copied += 1

    print(f"已拷贝 {copied} 个歌曲文件夹到 {len(packs)} 个曲包。")

    if copied == 0:
        print("警告: 没有可打包的歌曲文件夹（均需含 project.arcproj）。")
        return

    # 为每个曲包生成 pack.yml / index.yml 并放置封面
    for packkey, info in packs.items():
        display = info["display"]
        is_catchall = info["is_catchall"]

        if is_catchall:
            # 兜底包：内部文件夹用 Extra，封面回退 in/pack.png
            inner = "Extra"
            img_src = None
        else:
            canonical = info["canonical"]
            inner = sanitize(canonical)
            img_src = find_pack_image(songs_dir, canonical, inner)

        pack_root = os.path.join(packs_dir, packkey)
        inner_pack_dir = os.path.join(pack_root, inner)
        os.makedirs(inner_pack_dir, exist_ok=True)

        # 封面：官方包优先 songs/pack/1080_select_<set>.png，缺失回退 in/pack.png
        img_dst = os.path.join(inner_pack_dir, "pack.png")
        if img_src and os.path.isfile(img_src):
            shutil.copy2(img_src, img_dst)
        elif os.path.isfile(fallback_image):
            shutil.copy2(fallback_image, img_dst)
            if not is_catchall:
                print(f"  曲包 '{packkey}': 未找到 songs/pack 封面，回退使用 {fallback_image}")
        else:
            print(f"  曲包 '{packkey}': 未找到任何封面图片，pack.png 缺失")

        generate_pack_files(
            charts_dir=pack_root,
            pack_name=inner,
            publisher=publisher,
            image_name="pack.png",
            pack_display=display,
        )
        print(f"  曲包 '{packkey}' (显示名: {display}) 生成完成")

    print(f"\n所有曲包已生成于 {packs_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="按 songlist 的 set 字段将歌曲拆分为多个独立曲包。"
    )
    parser.add_argument("-i", "--charts-dir", default="tmp/charts", help="含歌曲子文件夹的目录 (默认: tmp/charts)")
    parser.add_argument("--songlist", default="tmp/songs/songlist", help="官方 songlist 路径 (默认: tmp/songs/songlist)")
    parser.add_argument("--packlist", default="tmp/songs/packlist", help="官方 packlist 路径 (默认: tmp/songs/packlist)")
    parser.add_argument("--songs-dir", default="tmp/songs", help="解压后的 songs 目录 (默认: tmp/songs)")
    parser.add_argument("--packs-dir", default="tmp/packs", help="拆分输出目录 (默认: tmp/packs)")
    parser.add_argument("-p", "--publisher", default="qings", help="发布者名称 (默认: qings)")
    parser.add_argument("--fallback-image", default="in/pack.png", help="缺失 songs/pack 封面时的回退图片 (默认: in/pack.png)")
    args = parser.parse_args()
    split_packs(
        charts_dir=args.charts_dir,
        songlist_path=args.songlist,
        packlist_path=args.packlist,
        songs_dir=args.songs_dir,
        packs_dir=args.packs_dir,
        publisher=args.publisher,
        fallback_image=args.fallback_image,
    )
