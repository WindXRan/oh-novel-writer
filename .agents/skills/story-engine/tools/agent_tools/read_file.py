"""read_file 工具：读取项目文件。路径相对于 base_dir 或绝对路径。"""

import os
from pathlib import Path


def read_file(path: str, base_dir: str = None) -> str:
    """读取文件内容。

    Args:
        path: 文件路径（相对于 base_dir 或绝对路径）
        base_dir: 基础目录，用于解析相对路径

    Returns:
        文件内容文本

    Raises:
        FileNotFoundError: 文件不存在
    """
    p = Path(path)
    if not p.is_absolute() and base_dir:
        p = Path(base_dir) / path
    p = p.resolve()

    if not p.exists():
        # 尝试 glob 匹配
        parent = p.parent
        name = p.name
        if parent.exists():
            matches = list(parent.glob(name))
            if matches:
                p = matches[0]

    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")

    if not p.is_file():
        raise IsADirectoryError(f"路径是目录: {p}")

    content = p.read_text(encoding="utf-8")

    # 对大文件截断
    max_chars = 15000
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n...（截断，原长 {len(content)} chars）"

    return content


TOOL_SCHEMA = {
    "name": "read_file",
    "fn": read_file,
    "description": "读取项目中的文件内容。支持相对路径（相对于项目根目录）和绝对路径。大文件自动截断到 15000 字符。",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，相对于项目根目录（如 projects/作者/书名/rewrites/新书名/concept.md）"
            }
        },
        "required": ["path"]
    }
}
