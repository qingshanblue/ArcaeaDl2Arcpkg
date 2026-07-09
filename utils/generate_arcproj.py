import os
import re
import json
import yaml
import argparse


def load_bpm_special_cases(yaml_path="in/bpmSpecialCasesList.yaml"):
    """读取手动维护的 BPM 覆盖表，键为歌曲文件夹名、值为 BPM（数值）。优先级最高。"""
    if not os.path.exists(yaml_path):
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {str(k).strip(): float(v) for k, v in data.items()}
    except Exception:
        return {}


def load_songlist(path="tmp/songs/songlist"):
    """读取官方 songlist（JSON），构建 id -> {bpm_base, bpm, ratings:{ratingClass:rating}}。优先级第二。"""
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
        ratings = {
            d["ratingClass"]: d.get("rating")
            for d in song.get("difficulties", [])
            if "ratingClass" in d
        }
        result[sid] = {
            "bpm_base": song.get("bpm_base"),
            "bpm": song.get("bpm"),
            "ratings": ratings,
            "artist": song.get("artist"),
            "title_localized": song.get("title_localized"),
            "search_title": song.get("search_title"),
        }
    return result


def fmt_bpm(value):
    """整型去小数，否则保留两位小数。"""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def fmt_rating(value):
    """定数整洁显示：整数去 .0，浮点保留。"""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def resolve_title(title_localized, search_title, folder_name):
    """标题取值优先级：title_localized(en 否则首个值) > search_title.ja[0] > search_title.ko[0] > 文件夹名。"""
    if isinstance(title_localized, dict):
        if "en" in title_localized and title_localized["en"]:
            return str(title_localized["en"])
        for v in title_localized.values():
            if v:
                return str(v)
    if isinstance(search_title, dict):
        for lang in ("ja", "ko"):
            lst = search_title.get(lang)
            if isinstance(lst, list) and lst:
                return str(lst[0])
    return folder_name


def yaml_scalar(value):
    """含 YAML 歧义字符(或起首为 '-')时加单引号，否则原样返回。单引号内需把 ' 双写转义。"""
    s = str(value)
    if (
        s == ""
        or s != s.strip()
        or s[0] in "-"
        or not re.fullmatch(r"[0-9A-Za-z_. /\-]+", s)
    ):
        return "'" + s.replace("'", "''") + "'"
    return s


def generate_arcproj_files(
    input_dir="tmp/charts",
    bpm_yaml="in/bpmSpecialCasesList.yaml",
    songlist_path="tmp/songs/songlist",
):
    if not os.path.exists(input_dir):
        print(f"错误: 文件夹 '{input_dir}' 不存在！请先运行之前的整理脚本。")
        return

    bpm_special_cases = load_bpm_special_cases(bpm_yaml)
    songlist = load_songlist(songlist_path)

    # 定义各难度的基名和颜色 (包含了 Beyond 和 Eternal 以防万一)
    difficulties = {
        0: ("Past", "#3A6B78FF"),
        1: ("Present", "#566947FF"),
        2: ("Future", "#482B54FF"),
        3: ("Beyond", "#505058FF"),
        4: ("Eternal", "#823E69FF"),
    }

    # ---------- 初始化计数器 ----------
    total_folders = 0
    generated_count = 0
    skipped_count = 0

    # 遍历每个谱面文件夹
    for folder_name in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        total_folders += 1

        # 找出文件夹中所有的数字命名的 .aff 文件 (如 0.aff, 1.aff)
        chart_indices = []
        for f in os.listdir(folder_path):
            match = re.match(r"^(\d+)\.aff$", f)
            if match:
                chart_indices.append(int(match.group(1)))

        if not chart_indices:
            # 如果没有谱面文件，跳过该文件夹
            skipped_count += 1
            continue

        chart_indices.sort()

        # 检测视频文件：若存在 .mp4（后缀匹配，忽略大小写）则重命名为 base.mp4
        video_path = None
        for entry in os.listdir(folder_path):
            if entry.lower().endswith(".mp4"):
                src = os.path.join(folder_path, entry)
                dst = os.path.join(folder_path, "base.mp4")
                if os.path.abspath(src) != os.path.abspath(dst):
                    if not os.path.exists(dst):
                        try:
                            os.replace(src, dst)
                        except OSError:
                            pass
                video_path = "base.mp4"
                break

        # BPM 取值优先级：手动覆盖表 > songlist(bpm_base) > 否则报错终止
        if folder_name in bpm_special_cases:
            folder_bpm = fmt_bpm(bpm_special_cases[folder_name])
            bpm_text = folder_bpm
        elif folder_name in songlist:
            info = songlist[folder_name]
            if info.get("bpm_base") is None:
                print(f"❌ 错误: 歌曲 '{folder_name}' 在 songlist 中缺少 bpm_base，终止程序。")
                raise SystemExit(1)
            folder_bpm = fmt_bpm(float(info["bpm_base"]))
            raw_bpm = info.get("bpm")
            bpm_text = str(raw_bpm) if raw_bpm is not None else folder_bpm
            # 经 yaml_scalar 统一处理：含空格/'-'/歧义字符时加单引号并转义内部单引号
            bpm_text = yaml_scalar(bpm_text)
        else:
            print(f"❌ 错误: 未获取到歌曲 '{folder_name}' 的 BPM 信息（手动覆盖表与 songlist 均无），终止程序。")
            raise SystemExit(1)

        # 该歌曲的定数映射 ratingClass -> rating
        ratings = songlist.get(folder_name, {}).get("ratings", {})

        # 标题 / 作曲者：来自 songlist（artist 直接套用，title 按优先级解析）
        song_info = songlist.get(folder_name, {})
        if song_info:
            folder_composer = song_info.get("artist") or "N/A"
            folder_title = resolve_title(
                song_info.get("title_localized"),
                song_info.get("search_title"),
                folder_name,
            )
        else:
            folder_composer = "N/A"
            folder_title = folder_name

        # 封面临摹优先级：base.jpg > 1080_base.jpg（由 merge_songs 保证至少其一存在）
        if os.path.exists(os.path.join(folder_path, "base.jpg")):
            folder_jacket = "base.jpg"
        else:
            folder_jacket = "1080_base.jpg"

        # 开始构建 .arcproj 文件内容
        first_chart = f"{chart_indices[0]}.aff"
        arcproj_content = f"lastOpenedChartPath: {first_chart}\n"
        arcproj_content += "charts:\n"

        for idx in chart_indices:
            chart_filename = f"{idx}.aff"
            aff_path = os.path.join(folder_path, chart_filename)

            # 判断音频文件：优先使用对应难度的 X.ogg，没有则回退到 base.ogg
            audio_filename = f"{idx}.ogg"
            if not os.path.exists(os.path.join(folder_path, audio_filename)):
                audio_filename = "base.ogg"

            # 难度名 + 定数（ratingClass 对应 idx）
            if idx in difficulties:
                diff_base, diff_color = difficulties[idx]
            else:
                diff_base = f"Extra {idx}"
                diff_color = "#888888FF"
            rating = ratings.get(idx)
            if rating is not None:
                diff_name = f"{diff_base} {fmt_rating(rating)}"
                chart_constant = fmt_rating(rating)
            else:
                diff_name = f"{diff_base} ?"
                chart_constant = "?"

            # 拼接 YAML 格式内容
            arcproj_content += f"- chartPath: {chart_filename}\n"
            arcproj_content += f"  audioPath: {audio_filename}\n"
            arcproj_content += f"  jacketPath: {folder_jacket}\n"
            arcproj_content += f"  baseBpm: {folder_bpm}\n"
            arcproj_content += f"  bpmText: {bpm_text}\n"
            arcproj_content += "  syncBaseBpm: true\n"
            if video_path:
                arcproj_content += "  videoPath: base.mp4\n"
            arcproj_content += f"  title: {yaml_scalar(folder_title)}\n"
            arcproj_content += f"  composer: {yaml_scalar(folder_composer)}\n"
            arcproj_content += f"  difficulty: {diff_name}\n"
            if re.fullmatch(r"[0-9.]+", chart_constant):
                arcproj_content += f"  chartConstant: {chart_constant}\n"
            else:
                arcproj_content += f"  chartConstant: '{chart_constant}'\n"
            arcproj_content += f"  difficultyColor: '{diff_color}'\n"
            arcproj_content += "  skin:\n"
            arcproj_content += "    side: conflict\n"
            arcproj_content += "  previewEnd: 5000\n"

        # 写入 .arcproj 文件，统一命名为 project.arcproj
        arcproj_path = os.path.join(folder_path, "project.arcproj")
        with open(arcproj_path, "w", encoding="utf-8") as f:
            f.write(arcproj_content)

        generated_count += 1

    # ---------- 输出统计信息 ----------
    print(f"处理完成！共扫描 {total_folders} 个文件夹。")
    print(f"成功生成 {generated_count} 个 project.arcproj 文件。")
    if skipped_count > 0:
        print(f"跳过 {skipped_count} 个文件夹（无 .aff 谱面文件）。")
    print("")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="为每个歌曲文件夹生成 project.arcproj。"
    )
    parser.add_argument(
        "-i",
        "--charts-dir",
        default="tmp/charts",
        help="包含关卡子文件夹的目录 (默认: tmp/charts)",
    )
    parser.add_argument(
        "--bpm-yaml",
        default="in/bpmSpecialCasesList.yaml",
        help="BPM 覆盖表路径 (默认: in/bpmSpecialCasesList.yaml)",
    )
    parser.add_argument(
        "--songlist",
        default="tmp/songs/songlist",
        help="官方 songlist 文件路径 (默认: tmp/songs/songlist)",
    )
    args = parser.parse_args()
    generate_arcproj_files(
        input_dir=args.charts_dir,
        bpm_yaml=args.bpm_yaml,
        songlist_path=args.songlist,
    )
