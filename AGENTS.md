# AGENTS.md

将下载好的 Arcaea 谱面文件（`dl.zip`）转换为 ArcCreate 可用的 `.arcpkg` 曲包的流水线仓库。

## 环境与运行方式
- 使用 **pixi** 管理环境，唯一依赖 `pyyaml`。所有脚本都通过 `pixi run python <脚本>.py` 运行，不要直接用系统 python（可能缺 pyyaml）。
- `pixi.toml` 未定义 task，仅声明依赖。

## 目录布局
- `utils/`：所有脚本（`arcaea_charts_sort.py`、`generate_arcproj.py`、`generate_yml.py`、`merge_songs.py`、`etr2byd.py`）。
- `run.sh`：项目根目录的流水线入口脚本（原 `utils/convert.sh` 移动并重命名）。
- `in/`：输入区。`in/dl.zip`（下载的付费谱面压缩包，用户放置）、`in/songs.zip`（**必需**，解包官方 APK 得到的 `songs/`）、`in/pack.png`（封面 314x756）。`pack.png` 在 `.gitignore` 中加例外强制提交。
- `tmp/`：中间产物。`tmp/dl/`（解压 `dl.zip`）、`tmp/songs/`（解压 `songs.zip`）、`tmp/charts/`（整理并合并后的谱面）。
- `out/`：最终产物 `out/qings.zip` 与 `out/qings.arcpkg`。
- `in/`、`tmp/`、`out/` 均被 `.gitignore` 忽略（`in/` 下 `pack.png` 除外）。

## 完整流水线
- 一键执行：`bash run.sh`（从仓库根目录运行，CWD 决定相对路径；亲自按顺序跑下面各脚本，对产物做存在性判断，可重复运行幂等）。
- 步骤顺序（不能乱）：
  1. `pv in/dl.zip | bsdtar -xf - -C tmp`（得 `tmp/dl/`，用 pv 进度条代替逐文件清单刷屏）；若 `in/dl.zip` 缺失会交互询问/报错退出
  2. `pv in/songs.zip | bsdtar -xf - -C tmp`（得 `tmp/songs/`，**必需输入**，缺失则 `run.sh` 直接报错退出）
  3. `utils/arcaea_charts_sort.py --dl-dir tmp/dl --charts-dir tmp/charts`：按歌曲名分组，重命名整理到 `tmp/charts/<song>/`
  4. `utils/merge_songs.py --songs-dir tmp/songs --charts-dir tmp/charts`：把 `songs/` 合并进 `charts/`——`dl_` 开头的文件夹（如 `dl_name`）去前缀后补到 `charts/name/`；其余（免费歌曲）整文件夹拷贝；合并后每个 `charts/` 文件夹都含曲绘 `1080_base.jpg`
   5. `utils/generate_arcproj.py -i tmp/charts --songlist tmp/songs/songlist`：为每个歌曲文件夹生成 `project.arcproj`
   6. `utils/split_packs.py --charts-dir tmp/charts --songlist tmp/songs/songlist --packlist tmp/songs/packlist --songs-dir tmp/songs --publisher qings`：按 `songlist` 中每首歌的 `set` 字段拆分。先规范化 `set`：去掉末尾 `_append_<数字>` 段（如 `alice_append_1` → `alice`），使追加章节并入基础包。**仅当规范化后的 `set` 在 `packlist` 中有对应条目时各自成独立曲包**，写入 `tmp/packs/qings.<真实名>/`（`<真实名>` 取自 `packlist` 的 `name_localized`，en 否则首个值，空格转下划线、保留中文）。每个曲包自包含：根目录 `index.yml`、内部 `<canonical_set>/pack.yml`（`packName` 用真实名）+ `<canonical_set>/pack.png`（封面来自 `songs/pack/1080_select_<canonical_set>.png`，缺失则回退 `in/pack.png`）、以及各歌曲文件夹。规范化后 `set` 仍不在 `packlist` 中、但歌曲本身在 `songlist` 中（如 `single`）的，直接以该 `set` 值作为真实曲包名各自成独立包（显示名即 `set`，封面用 `songs/pack/1080_select_<set>.png`，缺失则回退 `in/pack.png`）。只有完全不在 `songlist` 中（查不到 set）的歌曲，才统一收进兜底曲包 `tmp/packs/qings.Extra/`（显示名 `Extra`，封面用 `in/pack.png`，不独立成包）。复用 `generate_yml.py` 的 `generate_pack_files` 生成每个包的 `pack.yml`/`index.yml`。
   7. 遍历 `tmp/packs/*`，逐个压缩为 `out/qings.<真实名>.zip` 并重命名为 `out/qings.<真实名>.arcpkg`（文件夹名即真实名；不再生成单个 `qings.arcpkg`）。

## 输入/输出约定
- 提交进仓库的只有：`utils/` 下脚本、`run.sh`、`in/pack.png`；生成物 `in/dl.zip`、`tmp/`、`out/` 均忽略。
- 下载文件命名规则（`arcaea_charts_sort.py` 依赖）：`name_audio_0..4`（ogg 音频）、`name_0..4`（.aff 谱面）、以及无扩展名的基础音频 `name`。整理后重命名为 `<song>/0.aff..4.aff`、`0.ogg..4.ogg`、`base.ogg`（优先用对应难度的 `X.ogg`，否则回退 `base.ogg`）。
- `generate_yml.py` 提供 `generate_pack_files(charts_dir, pack_name, publisher, image_name, pack_display)`：在 `charts_dir` 下创建内部包文件夹 `pack_name/`，写入 `pack.yml`（`packName` 用 `pack_display`，否则回退 `pack_name`）与 `index.yml`，扫描同级含 `project.arcproj` 的歌曲文件夹纳入。被 `split_packs.py` 复用，对每个 `tmp/packs/qings.<真实名>` 调用一次（`pack_name=<set>`，`pack_display` 取自 `packlist`）。

## 易踩的坑
- `generate_arcproj.py` 的 BPM 来源为官方 `tmp/songs/songlist` 的 `bpm_base`：命中时 `baseBpm` 取 `bpm_base` 数值，`bpmText` 取 songlist 原始 `bpm` 字符串（如 `"75 - 210"` 保留区间）；歌曲不在 `songlist` 或 `songlist` 中缺少 `bpm_base` 时**直接报错并终止程序**（不再有默认 160，也无手动覆盖表）。
- 难度 `difficulty` 的定数来自 songlist 中 `difficulties[].rating`（按 `ratingClass` 对应难度序号 0..4），拼成如 `Past 9.6`；songlist 无该难度则保留 `?` 占位符。每个难度还会写入 `chartConstant: <同一定数值>`（数值不加引号，`?` 时加单引号）。颜色仍含 `?`，需后续手工修正（如 `#3A6B78FF`）。
- `merge_songs.py` 依赖 `songs/` 内文件夹名：`dl_` 开头的去前缀补到对应 `charts/name/`，其余整文件夹拷贝；它只处理目录，无后缀的 `songlist` 等文件会被跳过；名为 `tutorial`、`random`、`pack` 的文件夹整目录跳过，不进入 `charts/`。
- `etr2byd.py`（把 `4.aff` 重命名为 `3.aff`，ETR→BYD）在 `run.sh` 中已被注释禁用；它支持 `--dry-run`/`--force`/`--verbose`，需要时手动运行。
- `generate_arcproj.py` 会对含视频的歌曲做处理：若文件夹内有 `.mp4`（后缀大小写不敏感），重命名为 `base.mp4` 并在每个难度的 `project.arcproj` 中追加 `videoPath: base.mp4`；无视频则不加该字段。幂等：已是 `base.mp4` 或已存在 `base.mp4` 时不会覆盖。
- 每个含曲绘的歌曲文件夹在生成 `project.arcproj` 时都会写入 `jacketPath`，封面临摹优先级为 `base.jpg` > `1080_base.jpg`（取存在的那一个）。
- `title` 与 `composer` 也由 songlist 自动填充（按 `folder_name == id` 匹配）：`composer` 直接取 `artist` 字符串；`title` 优先级为 `title_localized`（优先 `en`，否则首个值）> `search_title.ja[0]` > `search_title.ko[0]` > 回退文件夹名。songlist 无该歌曲时 `title` 用文件夹名、`composer` 为 `N/A`。`title`/`composer` 含 YAML 歧义字符（非 ASCII、冒号、井号、首尾空格、起首 `-` 等）时整体加单引号；值内部的单引号会被转义为 `''`，否则 ArcCreate 的 YAML 解析会报 `did not find expected key`。
- 封面 `pack.png` 尺寸为 314x756，复制步骤会跳过已存在的情况。
