"""chapter_metrics 工具：获取章节指标（字数、AI痕迹等）。"""

import re
from pathlib import Path

from lib.text_metrics import count_metrics, get_body_chars
from lib.constants import AI_MARKERS


def chapter_metrics(chapter_num: int, config: dict = None) -> str:
    """获取指定章节的文本指标。

    Args:
        chapter_num: 章节号
        config: 配置字典（由 runtime 传入）

    Returns:
        指标报告文本
    """
    if not config:
        return "错误：未提供 config"

    ch_dir = Path(f"{config['rewrites_dir']}/chapters")
    ch_file = ch_dir / f"ch_{chapter_num:03d}.txt"

    if not ch_file.exists():
        return f"第{chapter_num}章文件不存在: {ch_file}"

    text = ch_file.read_text(encoding="utf-8")
    metrics = count_metrics(text)
    chars = get_body_chars(text)

    # 源文参考字数
    from utils import get_source_text, count_source_chars
    src_chars = count_source_chars(config, chapter_num)

    report = [
        f"第{chapter_num}章 指标:",
        f"  正文字数: {chars}",
        f"  源文字数: {src_chars}",
    ]
    if src_chars > 0:
        dev = (chars - src_chars) / src_chars
        report.append(f"  字数偏差: {dev:+.0%}")
        report.append(f"  目标范围: {int(src_chars*0.9)}~{int(src_chars*1.1)}")

    report.append(f"  段落数: {metrics['paragraphs']}")
    report.append(f"  对话行: {metrics['dialogue_lines']}")
    report.append(f"  AI路标词: {metrics['ai_markers']}")
    report.append(f"  比喻数: {metrics['metaphor']}")
    report.append(f"  直抒情: {metrics['direct_emotion']}")

    # AI 痕迹词检测
    ai_traces = []
    for marker in AI_MARKERS:
        pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        found = re.findall(pat, text)
        if found:
            ai_traces.append(f"{marker}x{len(found)}")
    if ai_traces:
        report.append(f"  AI痕迹词: {', '.join(ai_traces)}")
    else:
        report.append(f"  AI痕迹词: 无")

    return "\n".join(report)


TOOL_SCHEMA = {
    "name": "chapter_metrics",
    "fn": chapter_metrics,
    "description": "获取已写章节的文本指标（正文字数、源文字数、字数偏差、段落数、对话行数、AI路标词、比喻数、直抒情数、AI痕迹词）。写章后用于校验字数是否符合 target。",
    "parameters": {
        "type": "object",
        "properties": {
            "chapter_num": {
                "type": "integer",
                "description": "章节号（整数）"
            }
        },
        "required": ["chapter_num"]
    }
}
