#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送到 findwoods.github.io 仓库（排除 2生活照片存档 文件夹）
双击运行此脚本即可推送
"""

import subprocess
import os
import sys

REPO_PATH = r"D:\Columbia\findwoods\findwoods.github.io"

def run_git(*args):
    """执行 git 命令并打印输出"""
    cmd = ["git"] + list(args)
    print(f">>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_PATH, capture_output=True, text=True, encoding='utf-8')
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode

def main():
    print("=" * 50)
    print("  推送到 findwoods.github.io 仓库")
    print("  （排除 2生活照片存档 文件夹）")
    print("=" * 50)
    print()
    
    os.chdir(REPO_PATH)
    
    print("[1/3] 添加所有更改...")
    run_git("add", ".")
    
    print("\n[2/3] 提交更改...")
    run_git("commit", "-m", "Auto-sync after Windows file changes")
    
    print("\n[3/3] 推送到 GitHub...")
    run_git("push", "origin", "main")
    
    print("\n" + "=" * 50)
    print("  完成！")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        input("\n按 Enter 键退出...")
