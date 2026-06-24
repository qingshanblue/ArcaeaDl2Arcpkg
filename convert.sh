echo "整理dl/，按不同歌曲分为不同文件夹"
pixi run python arcaea_charts_sort.py

echo "将etr转换为byd，ARCcreate不支持读取ETR"
pixi run python etr2byd.py

echo "生成arcproj，才可被ARCcreate读取"
pixi run python generate_arcproj.py

echo "生成yml，组织所有歌曲为曲包方便使用"
pixi run python generate_yml.py

echo "压缩\"./charts/\"下的所有文件为zip并命名为qings.zip放在当前目录"
(cd ./charts && zip -r ../qings.zip .)

echo "重命名qings.zip为qings.arcpkg"
mv qings.zip qings.arcpkg