import os
import argparse
from pathlib import Path
import yaml


def generate_pack_files(
    charts_dir="charts", pack_name="qings", publisher="qings", image_name="pack.png"
):
    """
    扫描 charts 目录下的关卡文件夹，生成 pack.yml 和 index.yml。

    :param charts_dir: 包含关卡子文件夹的目录 (默认为 'charts')
    :param pack_name: 包文件夹名称及包显示名称 (默认为 'qings')
    :param publisher: 发布者名称，用于构造 identifier (如 'qings')
    :param image_name: 包封面图片文件名 (默认为 'pack.png')
    """
    charts_path = Path(charts_dir)
    if not charts_path.is_dir():
        print(f"错误: 目录 '{charts_dir}' 不存在！")
        return False

    # 1. 创建包文件夹，例如 charts/qings/
    pack_folder_path = charts_path / pack_name
    pack_folder_path.mkdir(parents=True, exist_ok=True)

    level_identifiers = []
    assets_for_index = []

    print("开始扫描关卡文件夹...")
    # 2. 扫描所有关卡文件夹，收集 identifier
    for item in charts_path.iterdir():
        # 必须是文件夹，且不能是 pack 文件夹本身
        if item.is_dir() and item.name != pack_name:
            arcproj_file = item / "project.arcproj"
            if arcproj_file.is_file():
                level_name = item.name
                # 生成 identifier: publisher.levelName
                safe_level_name = level_name.replace(" ", "").replace("_", "")
                identifier = f"{publisher}.{safe_level_name}"

                level_identifiers.append(identifier)

                # 为 index.yml 添加 level 类型的资产声明
                assets_for_index.append(
                    {
                        "directory": level_name,
                        "identifier": identifier,
                        "settingsFile": "project.arcproj",
                        "version": 0,
                        "type": "level",
                    }
                )
                print(f"  找到关卡: {level_name} -> {identifier}")
            else:
                print(f"  跳过文件夹 '{item.name}': 缺少 project.arcproj")

    if not level_identifiers:
        print(
            f"警告: 在 '{charts_dir}' 中未找到任何有效的关卡文件夹！pack.yml 的 levelIdentifiers 将为空。"
        )

    # 3. 生成 pack.yml 内容
    pack_identifier = f"{publisher}.{pack_name}"
    pack_data = {
        "packName": pack_name,
        "imagePath": image_name,
        "levelIdentifiers": level_identifiers,
    }

    # 写入 pack.yml 到 charts/qings/pack.yml
    pack_yml_path = pack_folder_path / "pack.yml"
    try:
        with open(pack_yml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                pack_data,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        print(f"\n[成功] 已生成包配置文件: {pack_yml_path}")
        print(
            f"  -> 请确保封面图片 '{image_name}' 已放在 '{pack_folder_path}/' 目录下。"
        )
    except Exception as e:
        print(f"错误: 写入 pack.yml 失败 - {e}")
        return False

    # 4. 将 pack 资产添加到 index 列表中
    assets_for_index.append(
        {
            "directory": pack_name,
            "identifier": pack_identifier,
            "settingsFile": "pack.yml",
            "version": 0,
            "type": "pack",
        }
    )

    # 5. 生成 index.yml 到 charts/index.yml
    index_yml_path = charts_path / "index.yml"
    try:
        with open(index_yml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                assets_for_index,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        print(f"[成功] 已生成索引文件: {index_yml_path}")
    except Exception as e:
        print(f"错误: 写入 index.yml 失败 - {e}")
        return False

    print("\n--- 下一步操作指南 ---")
    print(
        f"1. 请将你的包封面图片命名为 '{image_name}'，并放入 '{pack_folder_path}/' 文件夹。"
    )
    print(f"2. 进入 '{charts_dir}' 目录。")
    print(
        f"3. 选中所有文件和文件夹（包括各个关卡文件夹、'{pack_name}'文件夹和'index.yml'）。"
    )
    print(f"4. 将其压缩为 .zip 格式。")
    print(f"5. 将后缀名修改为 .arcpkg 即可完成打包！")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="生成 ArcCreate 关卡包的 pack.yml 和 index.yml 文件。"
    )
    parser.add_argument(
        "-i",
        "--input",
        default="charts",
        help="包含关卡子文件夹的输入目录 (默认: charts)",
    )
    parser.add_argument(
        "-p",
        "--publisher",
        default="qings",
        help="发布者名称，用于构造 identifier (默认: qings)",
    )
    parser.add_argument(
        "-n", "--name", default="qings", help="包文件夹名称及包显示名称 (默认: qings)"
    )
    parser.add_argument(
        "-img", "--image", default="pack.png", help="包封面图片文件名 (默认: pack.png)"
    )

    args = parser.parse_args()

    generate_pack_files(
        charts_dir=args.input,
        publisher=args.publisher,
        pack_name=args.name,
        image_name=args.image,
    )


if __name__ == "__main__":
    main()
