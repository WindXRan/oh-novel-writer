"""glob_files 工具：按模式搜索文件。"""

from pathlib import Path


def glob_files(pattern: str, base_dir: str = None) -> str:
    """按 glob 模式搜索文件。

    Args:
        pattern: glob 模式，如 "projects/**/concept.md" 或 "guides/plot_*.md"
        base_dir: 基础目录

    Returns:
        匹配的文件列表（每行一个路径）
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    matches = list(base.glob(pattern))

    if not matches:
        return "（无匹配文件）"

    # 限制返回数量
    lines = []
    for m in sorted(matches)[:50]:
        try:
            rel = m.relative_to(base)
            lines.append(str(rel))
        except ValueError:
            lines.append(str(m))

    if len(matches) > 50:
        lines.append(f"...（共 {len(matches)} 个）")

    return "\n".join(lines)


TOOL_SCHEMA = {
    "name": "glob_files",
    "fn": glob_files,
    "description": "按 glob 模式搜索项目中的文件。用于查找文件是否存在、定位文件路径。如 glob_files('**/concept.md') 找设定文件，glob_files('guides/plot_*.md') 找 plot_guide。",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "glob 搜索模式，如 '**/concept.md', 'guides/plot_*.md', 'chapters/ch_*.txt'"
            }
        },
        "required": ["pattern"]
    }
}
