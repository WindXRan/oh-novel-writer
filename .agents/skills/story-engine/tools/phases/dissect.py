"""Phase 0.75: 拆书。全本源文分析，输出给开书阶段消费。

流程：
1. 读 TOC → LLM 曲线分析选关键章（~15章）
2. 构建 _samples.txt + _key_chapters.json + _version.json
3. 5维度并行 API 分析
4. 提取开局摘要 → _opening_summary.md

版本：1
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import get_total_chapters, call_api, get_source_text
from state_manager import atomic_write_text
from prompt_loader import load_system_prompt, tag_output

DISSECT_VERSION = 1


DIMENSIONS = [
    {
        "name": "architecture",
        "label": "情节架构",
        "task": (
            "### 输出以下内容：\n\n"
            "1. **弧线阶段**：全书分为几个阶段？每个阶段的章节范围、情绪基调、密度\n"
            "2. **关键转折点**：章号、类型（决裂/反转/高潮/真相）、强度\n"
            "3. **情绪曲线**：逐章标注情绪标签，画出全书走势\n"
            "4. **节拍模式**：源文常用的节拍类型\n"
            "5. **## 开局分析**（前15章重点）：头5章怎样留住读者？前15章的钩子体系、节奏分配、角色引入节奏\n"
            "6. **收尾分析**（最后5章）：结局收束方式、弧线闭合情况\n\n"
            "===OPENING_SUMMARY===\n这里写前15章分析的紧凑摘要（3-5行），面向写章 agent 消费"
        ),
    },
    {
        "name": "conflict",
        "label": "冲突图谱",
        "task": (
            "### 输出以下内容：\n\n"
            "1. **主线冲突**：主要冲突类型（身份/利益/信息差/道德困境）及演变路径\n"
            "2. **冲突密度**：按阶段标注密度变化\n"
            "3. **冲突升级模式**：升级链条、情绪对应关系\n"
            "4. **## 开局分析**（前15章）：怎样引入冲突吸引读者\n"
            "5. **冲突替换建议**：每种冲突可换成的替代类型及强度\n\n"
            "===OPENING_SUMMARY===\n这里写前15章冲突分析的紧凑摘要（3-5行）"
        ),
    },
    {
        "name": "character_model",
        "label": "角色行为模型",
        "task": (
            "### 输出以下内容：\n\n"
            "为每个核心角色建立行为模型卡片（应激反应/决策模式/情感模式/弱点/成长弧线），"
            "并分析角色互动模式。基于跨前后章节的样本描述角色的变化。\n\n"
            "## 开局分析\n前15章角色引入方式、第一印象设计\n\n"
            "===OPENING_SUMMARY===\n这里写前15章角色引入的紧凑摘要（3-5行）"
        ),
    },
    {
        "name": "technique",
        "label": "写法特征",
        "task": (
            "### 输出以下内容：\n\n"
            "1. **钩子模式**：各类型占比，早期vs晚期变化\n"
            "2. **场景结构**：对话/叙事/描写比例\n"
            "3. **感官运用**：各感官占比\n"
            "4. **节奏特征**：句长、段落\n"
            "5. **视角**：POV选择\n"
            "6. **语言风格**：口语化程度、修辞\n"
            "7. **## 开局写法分析**（前15章重点）：开篇钩子、节奏、角色引入写法\n\n"
            "===OPENING_SUMMARY===\n这里写前15章写法的紧凑摘要（3-5行）"
        ),
    },
    {
        "name": "evaluation",
        "label": "源文评鉴",
        "task": (
            "### 输出以下内容：\n\n"
            "1. **赛道判定**：题材、品类、核心赛道特征\n"
            "2. **维度评分**（1-5分）：节奏、人设、冲突、爽点、文笔、钩子、完成度、赛道特征\n"
            "   ≥4分 → 对齐（必须继承），≤3分 → 改进（必须超越）\n"
            "3. **## 开局评价**（前15章专门分析）：留存力、开篇问题\n"
            "4. **核心成功因子**\n"
            "5. **必须改进**\n\n"
            "评分要有理有据。\n\n"
            "===OPENING_SUMMARY===\n这里写前15章评鉴的紧凑摘要（3-5行）"
        ),
    },
]


def _detect_curve_with_llm(config, api_key, api_url):
    """读 _toc.txt，用 LLM 分析情绪曲线，返回关键章节列表。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    toc_path = Path(base_dir) / "projects" / author / source_book / "_cache" / "_toc.txt"

    if not toc_path.exists():
        return _fallback_chapters(config)

    total_ch = get_total_chapters(config)
    toc_text = toc_path.read_text(encoding="utf-8")

    prompt = (
        f"读以下小说目录，分析情绪曲线，选出覆盖全书弧线的关键章节。\n\n"
        f"目录（共{total_ch}章）：\n{toc_text}\n\n"
        f"输出 JSON：\n"
        f"{{\n"
        f'  "phases": [{{"name": "", "start": 1, "end": 20, "emotion": "", "description": ""}}],\n'
        f'  "key_chapters": [1, ...],\n'
        f'  "reasoning": ""\n'
        f"}}\n\n"
        f"规则：第1章必选，每阶段至少2章，全书12-15章，不选相邻章。"
    )

    try:
        result = call_api(api_key, "deepseek-v4-flash", prompt, max_tokens=4096, api_url=api_url)
        m = re.search(r'\[[\d,\s]+\]', result)
        if m:
            chapters = json.loads(f"[{m.group(0).strip('[]')}]")
            valid = sorted(set(int(c) for c in chapters if 1 <= c <= total_ch))
            if len(valid) >= 3:
                return valid
    except Exception:
        pass

    return _fallback_chapters(config)


def _fallback_chapters(config):
    """等距采样（LLM 失败时降级）。"""
    total_ch = get_total_chapters(config)
    if total_ch <= 30:
        return list(range(1, total_ch + 1))
    selected = set()
    for c in range(1, 16):
        if c <= total_ch:
            selected.add(c)
    step = max(1, (total_ch - 15) // 12)
    for c in range(16, total_ch + 1, step):
        selected.add(c)
    for c in range(max(1, total_ch - 4), total_ch + 1):
        selected.add(c)
    return sorted(selected)


def _build_samples(config, key_chapters):
    """构建 _samples.txt 和 _key_chapters.json。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    out_dir = Path(base_dir) / "projects" / author / source_book / "_cache" / "source_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    total_ch = get_total_chapters(config)
    last5 = set(key_chapters[-5:])

    lines = []
    lines.append(f"===== 样本概况 =====")
    lines.append(f"全书共 {total_ch} 章，选了 {len(key_chapters)} 章")
    lines.append(f"覆盖范围：第{key_chapters[0]}章 → 第{key_chapters[-1]}章")
    lines.append(f"前15章: {len([c for c in key_chapters if c <= 15])} 章")
    lines.append(f"收尾: {len([c for c in key_chapters if c in last5])} 章")

    for ch in key_chapters:
        text = get_source_text(config, ch) or f"（第{ch}章读取失败）"
        tag = "开局" if ch <= 15 else ("收尾" if ch in last5 else "LLM选中")
        lines.append(f"\n===== 第{ch}章 (共{total_ch}章, {tag}) =====")
        lines.append(text)

    (out_dir / "_samples.txt").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "_key_chapters.json").write_text(
        json.dumps(key_chapters, ensure_ascii=False), encoding="utf-8"
    )
    # 版本追踪
    (out_dir / "_version.json").write_text(
        json.dumps({
            "dissect_version": DISSECT_VERSION,
            "timestamp": datetime.now().isoformat(),
            "total_chapters": total_ch,
            "sample_count": len(key_chapters),
        }, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  _samples.txt ({len(lines)}行), _key_chapters.json ({len(key_chapters)}章), _version.json")
    return out_dir


def _run_one_dimension(config, dim, samples_text, api_key, api_url):
    """运行一个分析维度。"""
    prompt = (
        f"分析下面源文的**{dim['label']}**维度。只分析不创作。\n\n"
        f"## 分析素材\n\n"
        f"{samples_text}\n\n"
        f"## 任务\n\n"
        f"{dim['task']}"
    )

    system_prompt = load_system_prompt("system-dissect.md")
    result = call_api(
        api_key, "deepseek-v4-flash", prompt,
        max_tokens=8192, system_prompt=system_prompt, api_url=api_url,
        temperature=0.6,
    )
    return dim["name"], tag_output(result.strip(), f"dissect-{dim['name']}")


def phase_dissect(config, state_mgr=None):
    """拆书：曲线分析 → 采样 → 5维度并行分析 → 开局摘要。"""
    print("\n" + "=" * 50)
    print("Phase 0.75: 拆书")
    print("=" * 50)

    if state_mgr and state_mgr.is_phase_done("dissect"):
        print("拆书已完成，跳过")
        return True

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY")

    from lib.api_client import get_api_url
    api_url = get_api_url(config)

    # Step 1: 曲线分析 → 选关键章
    print("  [1/4] 曲线分析中...")
    key_chapters = _detect_curve_with_llm(config, api_key, api_url)
    print(f"  -> 选定 {len(key_chapters)} 章: {key_chapters[:5]}...{key_chapters[-5:]}")

    # Step 2: 构建样本
    print("  [2/4] 构建样本...")
    out_dir = _build_samples(config, key_chapters)

    # Step 3: 5维度并行分析
    print(f"  [3/4] {len(DIMENSIONS)}维度并行分析...")
    samples_text = (out_dir / "_samples.txt").read_text(encoding="utf-8")

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_run_one_dimension, config, dim, samples_text, api_key, api_url): dim["name"]
            for dim in DIMENSIONS
        }
        for future in as_completed(futures):
            try:
                name, content = future.result()
                results[name] = content
            except Exception as e:
                failed = futures[future]
                print(f"  [FAIL] {failed}: {e}")

    for name, content in results.items():
        fpath = out_dir / f"{name}.md"
        atomic_write_text(fpath, content)
        lines = content.count("\n")
        print(f"  [OK] {name}.md ({lines}行)")

    # Step 4: 提取开局摘要 → _opening_summary.md
    print("  [4/4] 提取开局摘要...")
    _extract_opening_summary(out_dir)

    if state_mgr:
        state_mgr.phase_done("dissect")
    return True


def _extract_opening_summary(out_dir):
    """从各维度分析文件中提取 ===OPENING_SUMMARY=== 标签内容。"""
    parts = []
    dim_order = ["architecture", "conflict", "character_model", "technique", "evaluation"]
    dim_labels = {
        "architecture": "情节架构", "conflict": "冲突图谱",
        "character_model": "角色行为模型", "technique": "写法特征", "evaluation": "源文评鉴",
    }
    for name in dim_order:
        fp = out_dir / f"{name}.md"
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        m = re.search(r'===OPENING_SUMMARY===\s*(.+?)(?:\n\n|\Z)', content, re.DOTALL)
        if m:
            summary = m.group(1).strip()
            if summary:
                label = dim_labels.get(name, name)
                parts.append(f"### {label}\n{summary}")

    if parts:
        summary = "# 开局分析摘要\n\n适用于第1-15章写章/导图阶段。各维度视角的开局结论：\n\n" + "\n\n".join(parts)
        (out_dir / "_opening_summary.md").write_text(summary, encoding="utf-8")
        print(f"  [OK] _opening_summary.md ({len(parts)}/5 维度有摘要)")
    else:
        # 兜底
        fallback = "# 开局分析摘要\n\n（拆书未产出开局摘要，写章时无额外分析注入）\n"
        (out_dir / "_opening_summary.md").write_text(fallback, encoding="utf-8")
        print(f"  [WARN] _opening_summary.md 降级（无维度输出OPENING_SUMMARY）")
