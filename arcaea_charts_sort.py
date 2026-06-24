import os
import shutil
import re


def organize_arcaea_files():
    dl_dir = "dl"
    charts_dir = "charts"

    if not os.path.exists(dl_dir):
        print(f"错误: 文件夹 '{dl_dir}' 不存在！")
        return

    # 创建 charts 总文件夹
    os.makedirs(charts_dir, exist_ok=True)

    # 匹配 name_audio_0 到 name_audio_4 的正则表达式 (优先匹配)
    pattern_audio_diff = re.compile(r"^(.*)_audio_(0|1|2|3|4)$")
    # 匹配 name_0 到 name_4 的正则表达式
    pattern_chart = re.compile(r"^(.*)_(0|1|2|3|4)$")

    files_to_process = []
    candidate_groups = set()

    # 第一遍扫描：收集文件，并提取所有可能的 "name" 基础名
    for f in os.listdir(dl_dir):
        fp = os.path.join(dl_dir, f)
        # 只处理文件，忽略无用文件夹和隐藏文件
        if os.path.isfile(fp) and not f.startswith("."):
            files_to_process.append(f)
            f_base, ext = os.path.splitext(f)

            match_audio = pattern_audio_diff.match(f_base)
            match_chart = pattern_chart.match(f_base)

            if match_audio:
                # 如果是 name_audio_X，提取前面的 name
                candidate_groups.add(match_audio.group(1))
            elif match_chart:
                # 如果是 name_X，提取前面的 name
                candidate_groups.add(match_chart.group(1))
            elif ext == "":
                # 如果没有扩展名，很可能是基础音乐文件 name
                candidate_groups.add(f_base)

    # 第二遍扫描：复制并重命名文件
    for f in files_to_process:
        f_base, ext = os.path.splitext(f)

        match_audio = pattern_audio_diff.match(f_base)
        match_chart = pattern_chart.match(f_base)

        group_name = ""
        dest_name = f  # 默认保持原文件名

        if match_audio:
            # 处理 name_audio_0 ~ name_audio_4 -> 0.ogg ~ 4.ogg
            group_name = match_audio.group(1)
            dest_name = f"{match_audio.group(2)}.ogg"
        elif match_chart:
            # 处理 name_0 ~ name_4 -> 0.aff ~ 4.aff
            group_name = match_chart.group(1)
            dest_name = f"{match_chart.group(2)}.aff"
        else:
            # 为其他文件查找最长匹配的基础名 (防止 name_xxx 被误判)
            best_match = ""
            for cand in candidate_groups:
                if f_base == cand or f_base.startswith(cand + "_"):
                    if len(cand) > len(best_match):
                        best_match = cand

            group_name = best_match if best_match else f_base

            # 处理基础音乐文件 name -> base.ogg
            if f_base == group_name and ext == "":
                dest_name = "base.ogg"
            else:
                # 处理其他文件：去掉 "name_" 前缀
                if f_base.startswith(group_name + "_"):
                    # 去掉 "group_name_"，保留后面的部分
                    remaining_name = f_base[len(group_name) + 1 :]
                    # 拼接回扩展名
                    dest_name = remaining_name + ext
                else:
                    # 如果不以 name_ 开头，保留原文件名
                    dest_name = f

        # 创建对应的谱面文件夹
        dest_dir = os.path.join(charts_dir, group_name)
        os.makedirs(dest_dir, exist_ok=True)

        # 复制文件
        src_path = os.path.join(dl_dir, f)
        dest_path = os.path.join(dest_dir, dest_name)

        print(f"复制: {f} -> charts/{group_name}/{dest_name}")
        # 使用 copy2 会保留文件的原始修改时间等元数据
        shutil.copy2(src_path, dest_path)

    print("全部复制并整理完成！")


if __name__ == "__main__":
    organize_arcaea_files()
