#!/usr/bin/env python3
"""
自动更新版本号、打tag并推送的脚本
用法：python scripts/update_version_and_tag.py 1.2.3
"""
import sys
import re
import subprocess
from pathlib import Path


def update_version(new_version):
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("pyproject.toml 不存在")
        sys.exit(1)
    content = pyproject.read_text(encoding="utf-8")
    new_content = re.sub(
        r'version\s*=\s*"[^"]*"', f'version = "{new_version}"', content
    )
    pyproject.write_text(new_content, encoding="utf-8")
    print(f"已更新 pyproject.toml 版本号为 {new_version}")


def run(cmd):
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"命令失败: {cmd}")
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("用法: python scripts/update_version_and_tag.py 1.2.3")
        sys.exit(1)
    version = sys.argv[1]
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print("版本号格式错误，应为 x.y.z")
        sys.exit(1)
    update_version(version)
    run("git add pyproject.toml")
    run(f'git commit -m "Bump version to {version}"')
    run(f"git tag v{version}")
    run("git push")
    run("git push --tags")
    print(f"已提交、打tag并推送 v{version}")


if __name__ == "__main__":
    main()
