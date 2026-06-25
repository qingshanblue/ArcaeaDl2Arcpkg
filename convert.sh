echo "0. 解压dl.zip"
unzip ./dl.zip && echo

echo "1. 整理dl/中，按不同歌曲分为不同文件夹"
pixi run python arcaea_charts_sort.py

echo "2. 将etr转换为byd，ARCcreate不支持读取ETR"
pixi run python etr2byd.py

echo "3. 生成arcproj，才可被ARCcreate读取"
pixi run python generate_arcproj.py

echo "4. 生成yml，组织所有歌曲为曲包方便使用"
pixi run python generate_yml.py

echo "5. 复制图片pack.png(314x756)到曲包文件夹"
if [ -f "./charts/qings/pack.png" ]; then
    echo $"pack.png 已存在，跳过复制" && echo
else
    cp ./pack.png ./charts/qings/pack.png && echo $"复制完成" && echo
fi

echo "6. 压缩\"./charts/\"下的所有文件为zip并命名为qings.zip放在当前目录"
if [ -f "./qings.zip" ] || [ -f "./qings.arcpkg" ]; then
    echo $"qings.zip 或 qings.arcpkg 已存在，跳过压缩" && echo
else
    (cd ./charts && zip -rq - . | pv -s $(du -sb . | awk '{print $1}') > ../qings.zip) && echo $"压缩完成" && echo
fi

echo "7. 重命名qings.zip为qings.arcpkg"
if [ -f "./qings.arcpkg" ]; then
    echo $"qings.arcpkg 已存在，跳过重命名" && echo
else
    mv qings.zip qings.arcpkg && echo $"重命名完成" && echo
fi

echo "0. 转换完成"
