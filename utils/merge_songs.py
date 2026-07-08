import os
import shutil
import argparse


def copy_tree(src, dest):
    """递归把 src 下的内容合并拷贝到 dest（已存在文件覆盖）。"""
    os.makedirs(dest, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = os.path.join(dest, rel) if rel != "." else dest
        os.makedirs(target_root, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root, f), os.path.join(target_root, f))


def merge_songs(songs_dir="tmp/songs", charts_dir="tmp/charts"):
    if not os.path.isdir(songs_dir):
        print(f"错误: 文件夹 '{songs_dir}' 不存在！请先解压 in/songs.zip。")
        return

    os.makedirs(charts_dir, exist_ok=True)

    dl_count = 0
    free_count = 0

    for entry in os.listdir(songs_dir):
        src = os.path.join(songs_dir, entry)
        if not os.path.isdir(src):
            # 跳过无后缀文件（songlist 等）
            continue

        # tutorial 是新手教程，不是正式歌曲，不拷贝进 charts/
        if entry == "tutorial":
            continue

        if entry.startswith("dl_"):
            # 付费歌曲的额外信息：去掉 dl_ 前缀后合并进对应 charts/<name>/
            name = entry[3:]
            dest = os.path.join(charts_dir, name)
            copy_tree(src, dest)
            dl_count += 1
        else:
            # 免费歌曲：整个文件夹拷贝到 charts/ 下
            dest = os.path.join(charts_dir, entry)
            copy_tree(src, dest)
            free_count += 1

    print(f"合并完成！处理 {dl_count} 个 dl_ 额外信息文件夹，{free_count} 个免费歌曲文件夹。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="将解压后的 songs/ 合并进 charts/：dl_ 开头文件夹补到对应付费歌曲，其余整体拷贝。"
    )
    parser.add_argument(
        "--songs-dir", default="tmp/songs", help="解压后的 songs 目录 (默认: tmp/songs)"
    )
    parser.add_argument(
        "--charts-dir", default="tmp/charts", help="整理输出的目录 (默认: tmp/charts)"
    )
    args = parser.parse_args()
    merge_songs(songs_dir=args.songs_dir, charts_dir=args.charts_dir)
