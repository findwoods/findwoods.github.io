@echo off
cd /d D:\Columbia\findwoods\findwoods.github.io



echo Running "更新目录.py"...
python "更新目录.py"

echo Adding all changes...
git add .

echo Committing changes...
git commit -m "Auto-sync after Windows file changes"

echo Pushing to GitHub...
git push origin main

pause
