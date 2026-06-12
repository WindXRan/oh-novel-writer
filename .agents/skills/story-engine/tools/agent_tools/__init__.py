"""Agent 工具集。所有工具函数和 schema 集中注册。

用法：
    from agent_tools import get_default_tools
    tool_defs = get_default_tools(config)

    # 批量注册到 runtime
    runtime.register_tools(tool_defs)
"""

from agent_tools.read_file import TOOL_SCHEMA as READ_FILE, read_file
from agent_tools.write_file import TOOL_SCHEMA as WRITE_FILE, write_file
from agent_tools.glob_files import TOOL_SCHEMA as GLOB_FILES, glob_files
from agent_tools.search_content import TOOL_SCHEMA as SEARCH_CONTENT, search_content
from agent_tools.chapter_metrics import TOOL_SCHEMA as CHAPTER_METRICS, chapter_metrics
from agent_tools.finish import TOOL_SCHEMA as FINISH, finish


__all__ = [
    "get_default_tools",
    "get_write_chapter_tools",
    "read_file", "write_file", "glob_files",
    "search_content", "chapter_metrics", "finish",
]


def _bind_fn(schema, **bind_kwargs):
    """将 schema 中的 fn 绑定额外参数。"""
    fn = schema["fn"]

    def bound_fn(**kwargs):
        merged = {**bind_kwargs, **kwargs}
        return fn(**merged)

    return {
        "name": schema["name"],
        "fn": bound_fn,
        "description": schema["description"],
        "parameters": schema["parameters"],
    }


def get_default_tools(config: dict = None) -> list[dict]:
    """获取默认工具集（所有通用工具）。

    Args:
        config: 配置字典，绑定到需要 config 的工具

    Returns:
        [{name, fn, description, parameters}, ...]
    """
    tools = [
        READ_FILE,
        WRITE_FILE,
        GLOB_FILES,
        SEARCH_CONTENT,
        FINISH,
    ]

    # 需要 config 的工具绑定 config
    if config:
        tools.append(_bind_fn(CHAPTER_METRICS, config=config))

    return tools


def get_write_chapter_tools(config: dict) -> list[dict]:
    """获取写章专用的工具集（含 chapter_metrics）。

    Args:
        config: 配置字典

    Returns:
        [{name, fn, description, parameters}, ...]
    """
    tools = get_default_tools(config)
    return tools
