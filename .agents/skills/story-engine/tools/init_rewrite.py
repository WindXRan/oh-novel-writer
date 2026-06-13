"""初始化新仿写项目：自动检测同名冲突 → 去重命名 → 生成 config。"""

import os
import sys
import json
import argparse
from pathlib import Path


def find_existing_projects(base_dir, author, source_book):
    """扫描 rewrites/ 下已有项目名，返回 set。"""
    rewrites_dir = Path(base_dir) / "projects" / author / source_book / "rewrites"
    if not rewrites_dir.exists():
        return set()
    return {p.name for p in rewrites_dir.iterdir() if p.is_dir()}


def pick_project_name(book_name, existing):
    """如果 book_name 已存在，自动追加 -v2、-v3……"""
    name = book_name
    if name not in existing:
        return name
    v = 2
    while f"{book_name}-v{v}" in existing:
        v += 1
    return f"{book_name}-v{v}"


def generate_config(author, source_book, book_name, project_name, base_dir):
    """生成 config dict。"""
    rewrites_dir = f"projects/{author}/{source_book}/rewrites/{project_name}"
    config_name = f"config_rewrite_{author}_{project_name}.json"
    return {
        "book_name": book_name,
        "author": author,
        "source_book": source_book,
        "api_key": None,
        "model": "deepseek-v4-flash",
        "reasoning_effort": "low",
        "prompts_dir": ".agents/skills/story-engine/prompts",
        "rewrites_dir": rewrites_dir,
    }, config_name


def main():
    parser = argparse.ArgumentParser(description="初始化新仿写项目")
    parser.add_argument("--author", required=True, help="作者名")
    parser.add_argument("--source", required=True, help="源书名（目录名）")
    parser.add_argument("--book", required=True, help="新书书名")
    parser.add_argument("--base-dir", default=os.getcwd(), help="项目根目录")
    args = parser.parse_args()

    base_dir = args.base_dir
    author = args.author
    source_book = args.source
    book_name = args.book

    # 检测源书是否存在
    src_dir = Path(base_dir) / "projects" / author / source_book
    if not src_dir.exists():
        print(f"[FAIL] 源书目录不存在: {src_dir}")
        sys.exit(1)

    # 扫描现有项目
    existing = find_existing_projects(base_dir, author, source_book)
    project_name = pick_project_name(book_name, existing)

    if project_name != book_name:
        print(f"  [INFO] 项目名 '{book_name}' 已存在，自动重命名为 '{project_name}'")

    config, config_name = generate_config(author, source_book, book_name, project_name, base_dir)

    # 写入 config
    config_dir = Path(base_dir) / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / config_name
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print(f"\n[OK] config: {config_path}")
    print(f"[OK] 项目名: {project_name}")
    print(f"[OK] rewrites_dir: {config['rewrites_dir']}")
    print(f"\n下一步:")
    print(f"  python pipeline.py --config {config_path} --phase all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
