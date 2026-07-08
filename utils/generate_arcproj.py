import os
import re
import yaml
import argparse


def load_bpm_special_cases(yaml_path="in/bpmSpecialCasesList.yaml"):
    """读取手动维护的 BPM 覆盖表，键为歌曲文件夹名，值为 BPM（数值）。"""
    if not os.path.exists(yaml_path):
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {str(k).strip(): float(v) for k, v in data.items()}
    except Exception:
        return {}


def generate_arcproj_files(input_dir="tmp/charts", bpm_yaml="in/bpmSpecialCasesList.yaml"):
    if not os.path.exists(input_dir):
        print(f"错误: 文件夹 '{input_dir}' 不存在！请先运行之前的整理脚本。")
        return

    bpm_special_cases = load_bpm_special_cases(bpm_yaml)

    # 定义各难度的名称和颜色 (包含了 Beyond 和 Eternal 以防万一)
    difficulties = {
        0: ("Past ?", "#3A6B78FF"),
        1: ("Present ?", "#566947FF"),
        2: ("Future ?", "#482B54FF"),
        3: ("Beyond ?", "#505058FF"),
        4: ("Eternal ?", "#823E69FF"),
    }

    # 提取 BPM 的函数：尝试从 .aff 文件头读取真实 BPM，并换算为等效四分音符(4/4拍)BPM
    def get_bpm_from_aff(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                # 逐行读取前几行，寻找 timing 语句
                for _ in range(10):
                    line = file.readline()
                    if not line:
                        break
                    # 匹配类似 timing(0,188.00,4.00); 或 Timing(0,100,2);
                    # 提取 bpm (第2个参数) 和 beat (第3个参数)
                    match = re.search(
                        r"timing\s*\(\s*0\s*,\s*([\d.]+)\s*,\s*([\d.]+)",
                        line,
                        re.IGNORECASE,
                    )
                    if match:
                        bpm_val = float(match.group(1))
                        beat_val = float(match.group(2))

                        # 计算等效四分音符 BPM: bpm * (4 / beat)
                        # 如果 beat 为 0 防止报错
                        if beat_val != 0:
                            equivalent_bpm = bpm_val * (4.0 / beat_val)
                        else:
                            equivalent_bpm = bpm_val

                        # 格式化输出：如果是整数则去掉小数点，否则保留两位小数
                        if equivalent_bpm == int(equivalent_bpm):
                            return str(int(equivalent_bpm))
                        else:
                            return f"{equivalent_bpm:.2f}"
        except Exception:
            pass
        return "160"  # 如果读取失败，返回默认值 160

    # ---------- 新增：初始化计数器 ----------
    total_folders = 0  # 遍历的文件夹总数（包括跳过的）
    generated_count = 0  # 成功生成 .arcproj 的文件夹数量
    skipped_count = 0  # 因没有谱面文件而跳过的文件夹数量

    # 遍历每个谱面文件夹
    for folder_name in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        total_folders += 1  # 每遇到一个文件夹就计数

        # 找出文件夹中所有的数字命名的 .aff 文件 (如 0.aff, 1.aff)
        chart_indices = []
        for f in os.listdir(folder_path):
            match = re.match(r"^(\d+)\.aff$", f)
            if match:
                chart_indices.append(int(match.group(1)))

        if not chart_indices:
            # 如果没有谱面文件，跳过该文件夹
            skipped_count += 1  # 新增：跳过计数
            continue

        chart_indices.sort()

        # BPM 取值策略：命中覆盖表则整首歌套用同一值，否则按 .aff 解析
        if folder_name in bpm_special_cases:
            override_bpm = bpm_special_cases[folder_name]
            bpm_str = (
                str(int(override_bpm))
                if override_bpm == int(override_bpm)
                else f"{override_bpm:.2f}"
            )

            def bpm_getter(idx, aff_path):
                return bpm_str

        else:

            def bpm_getter(idx, aff_path):
                return get_bpm_from_aff(aff_path)

        # 开始构建 .arcproj 文件内容
        first_chart = f"{chart_indices[0]}.aff"
        arcproj_content = f"lastOpenedChartPath: {first_chart}\n"
        arcproj_content += "charts:\n"

        for idx in chart_indices:
            chart_filename = f"{idx}.aff"
            aff_path = os.path.join(folder_path, chart_filename)

            # 获取等效四分音符 BPM
            bpm = bpm_getter(idx, aff_path)

            # 判断音频文件：优先使用对应难度的 X.ogg，没有则回退到 base.ogg
            audio_filename = f"{idx}.ogg"
            if not os.path.exists(os.path.join(folder_path, audio_filename)):
                audio_filename = "base.ogg"

            # 获取难度信息
            if idx in difficulties:
                diff_name, diff_color = difficulties[idx]
            else:
                diff_name = f"Extra {idx} ?"
                diff_color = "#888888FF"

            # 拼接 YAML 格式内容
            arcproj_content += f"- chartPath: {chart_filename}\n"
            arcproj_content += f"  audioPath: {audio_filename}\n"
            arcproj_content += f"  baseBpm: {bpm}\n"
            arcproj_content += f"  bpmText: {bpm}\n"
            arcproj_content += "  syncBaseBpm: true\n"
            arcproj_content += f"  title: {folder_name}\n"
            arcproj_content += "  composer: N/A\n"
            arcproj_content += f"  difficulty: {diff_name}\n"
            arcproj_content += f"  difficultyColor: '{diff_color}'\n"
            arcproj_content += "  skin:\n"
            arcproj_content += "    side: conflict\n"
            arcproj_content += "  previewEnd: 5000\n"

        # 写入 .arcproj 文件，统一命名为 project.arcproj
        arcproj_path = os.path.join(folder_path, "project.arcproj")
        with open(arcproj_path, "w", encoding="utf-8") as f:
            f.write(arcproj_content)

        generated_count += 1  # 新增：成功生成计数

    # ---------- 新增：输出统计信息 ----------
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
    args = parser.parse_args()
    generate_arcproj_files(input_dir=args.charts_dir, bpm_yaml=args.bpm_yaml)
