"""search_content 工具：在文件中搜索内容。"""

import os
import re
from pathlib import Path


def search_content(pattern: str, path: str = ".", base_dir: str = None) -> str:
    """在指定路径下搜索匹配的内容。

    Args:
        pattern: 正则表达式或文本
        path: 搜索路径（相对于 base_dir）
        base_dir: 基础目录

    Returns:
        匹配结果列表
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    search_path = base / path

    if not search_path.exists():
        return f"路径不存在: {search_path}"

    try:
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    except re.error:
        compiled = re.compile(re.escape(pattern), re.IGNORECASE | re.DOTALL)

    results = []
    max_results = 30

    if search_path.is_file():
        files = [search_path]
    else:
        files = sorted(search_path.rglob("*.txt")) + sorted(search_path.rglob("*.md"))
        files = files[:200]  # 限制搜索文件数

    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            for m in compiled.finditer(text):
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                context = text[start:end].replace("\n", " ")
                try:
                    rel = fp.relative_to(base)
                except ValueError:
                    rel = fp
                results.append(f"{rel}: ...{context}...")
                if len(results) >= max_results:
                    break
        except Exception:
            continue
        if len(results) >= max_results:
            break

    if not results:
        return "（未找到匹配）"

    lines = "\n".join(results)
    return f"找到 {len(results)} 处匹配:\n{lines}"


TOOL_SCHEMA = {
    "name": "search_content",
    "fn": search_content,
    "description": "搜索文件内容。支持正则表达式。用于查找特定内容在项目中的位置。",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "搜索关键词或正则表达式，如 '女主'、'concept'"
            },
            "path": {
                "type": "string",
                "description": "搜索路径（默认为项目根目录）"
            }
        },
        "required": ["pattern"]
    }
}
