"""write_file 工具：写入文件。"""

from pathlib import Path


def write_file(path: str, content: str, base_dir: str = None) -> str:
    """写入文件内容。自动创建父目录。

    Args:
        path: 文件路径（相对或绝对）
        content: 要写入的内容
        base_dir: 基础目录

    Returns:
        写入确认信息
    """
    p = Path(path)
    if not p.is_absolute() and base_dir:
        p = Path(base_dir) / path
    p = p.resolve()

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

    return f"已写入 {p} ({len(content)} chars)"


TOOL_SCHEMA = {
    "name": "write_file",
    "fn": write_file,
    "description": "写入内容到指定文件。自动创建父目录。用于保存章节内容、guide 等产出。",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，相对于项目根目录"
            },
            "content": {
                "type": "string",
                "description": "要写入的文件内容"
            }
        },
        "required": ["path", "content"]
    }
}
