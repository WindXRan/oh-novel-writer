"""finish 工具：标记任务完成。"""


def finish(message: str = "") -> str:
    """完成任务并返回总结。

    Args:
        message: 完成总结

    Returns:
        确认信息
    """
    return f"[DONE] {message}"


TOOL_SCHEMA = {
    "name": "finish",
    "fn": finish,
    "description": "任务完成后调用此工具，传入完成总结。调用 finish 后 LLM 不应再输出其他内容。",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "完成总结信息"
            }
        }
    }
}
