@echo off
chcp 65001 >nul
cd /d D:\Columbia\findwoods\findwoods.github.io

echo ========================================
echo   推送到 findwoods.github.io 仓库
echo   （排除 2生活照片存档 文件夹）
echo ========================================
echo.

echo [1/3] 添加所有更改...
git add .

echo.
echo [2/3] 提交更改...
git commit -m "Auto-sync after Windows file changes"

echo.
echo [3/3] 推送到 GitHub...
git push origin main

echo.
echo ========================================
echo   完成！
echo ========================================
pause
