import os
import re


def generate_arcproj_files(input_dir="charts"):
    if not os.path.exists(input_dir):
        print(f"错误: 文件夹 '{input_dir}' 不存在！请先运行之前的整理脚本。")
        return

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

    # 遍历每个谱面文件夹
    for folder_name in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        # 找出文件夹中所有的数字命名的 .aff 文件 (如 0.aff, 1.aff)
        chart_indices = []
        for f in os.listdir(folder_path):
            match = re.match(r"^(\d+)\.aff$", f)
            if match:
                chart_indices.append(int(match.group(1)))

        if not chart_indices:
            # 如果没有谱面文件，跳过该文件夹
            continue

        chart_indices.sort()

        # 开始构建 .arcproj 文件内容
        first_chart = f"{chart_indices[0]}.aff"
        arcproj_content = f"lastOpenedChartPath: {first_chart}\n"
        arcproj_content += "charts:\n"

        # 记录当前关卡的主 BPM 用于最后在终端打印
        main_bpm = "160"

        for idx in chart_indices:
            chart_filename = f"{idx}.aff"
            aff_path = os.path.join(folder_path, chart_filename)

            # 1. 获取等效四分音符 BPM
            bpm = get_bpm_from_aff(aff_path)
            if idx == chart_indices[0]:
                main_bpm = bpm

            # 2. 判断音频文件：优先使用对应难度的 X.ogg，没有则回退到 base.ogg
            audio_filename = f"{idx}.ogg"
            if not os.path.exists(os.path.join(folder_path, audio_filename)):
                audio_filename = "base.ogg"

            # 3. 获取难度信息
            if idx in difficulties:
                diff_name, diff_color = difficulties[idx]
            else:
                diff_name = f"Extra {idx} ?"
                diff_color = "#888888FF"

            # 4. 拼接 YAML 格式内容
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

        print(
            f"已生成: {input_dir}/{folder_name}/project.arcproj (等效BPM: {main_bpm})"
        )


if __name__ == "__main__":
    generate_arcproj_files("charts")
