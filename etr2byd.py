#!/usr/bin/env python3
"""
etr2byd.py - 将目录树中所有名为 4.aff 的文件重命名为 3.aff
用法: python etr2byd.py [目录] [--dry-run] [--force] [--verbose]
"""

import os
import sys
import argparse
from pathlib import Path


def rename_files(root_dir, dry_run=False, force=False, verbose=False):
    """
    递归查找 root_dir 下所有名为 '4.aff' 的文件并重命名。

    Args:
        root_dir: 起始目录
        dry_run: 为 True 时只打印操作，不实际执行
        force:   为 True 时覆盖已存在的目标文件，否则跳过
        verbose: 为 True 时打印详细信息
    """
    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        print(f"错误：'{root_dir}' 不是一个有效目录", file=sys.stderr)
        sys.exit(1)

    # 收集所有符合条件的文件
    matches = list(root_path.rglob("4.aff"))
    if not matches:
        print(f"在 '{root_dir}' 中未找到任何 '4.aff' 文件")
        return

    print(f"找到 {len(matches)} 个 '4.aff' 文件")
    renamed_count = 0
    skipped_count = 0

    for src in matches:
        dst = src.with_name("3.aff")  # 替换文件名
        if verbose:
            print(f"  源文件: {src}")
            print(f"  目标: {dst}")

        # 如果目标已存在且不强制覆盖，则跳过
        if dst.exists() and not force:
            if verbose:
                print(f"  ⏭️  跳过：目标已存在 (使用 --force 强制覆盖)")
            skipped_count += 1
            continue

        # 执行重命名
        if dry_run:
            print(f"  [模拟] mv '{src}' -> '{dst}'")
        else:
            try:
                # 使用 os.replace 原子操作，跨文件系统安全
                os.replace(str(src), str(dst))
                renamed_count += 1
                if verbose:
                    print(f"  ✅ 重命名成功")
            except Exception as e:
                print(f"  ❌ 重命名失败: {e}", file=sys.stderr)

    # 总结
    if dry_run:
        print(
            f"\n模拟运行完成。将会重命名 {renamed_count} 个文件，跳过 {skipped_count} 个。"
        )
    else:
        print(f"\n实际重命名 {renamed_count} 个文件，跳过 {skipped_count} 个。")


def main():
    parser = argparse.ArgumentParser(
        description="将目录树中所有名为 4.aff 的文件重命名为 3.aff"
    )
    parser.add_argument(
        "directory", nargs="?", default=".", help="要搜索的根目录（默认为当前目录）"
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="仅显示将执行的操作，不实际修改文件",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制覆盖已存在的目标文件 (3.aff)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="显示详细的处理信息"
    )
    args = parser.parse_args()

    rename_files(args.directory, args.dry_run, args.force, args.verbose)


if __name__ == "__main__":
    main()
