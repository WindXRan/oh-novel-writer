"""Quality Gate: algorithmic checks + multi-agent review + gatekeeper.

Architecture:
  write → Phase 3.3 Quality Gate
    ├── 1. Algorithmic (Python, instant)
    │   ├── 字数 deviation
    │   ├── 对话占比
    │   └── 段落数
    ├── 2. Multi-Agent (4 parallel flash calls)
    │   ├── beat_audit      → 节拍顺序 vs plot_guide
    │   ├── content_audit   → 记忆点+钩子+擦边
    │   ├── peeling_audit   → 剥名后是否可识别
    │   └── character_audit → 人设一致性
    └── 3. Gatekeeper (Python)
        ├── All PASS → ✓
        ├── Any FAIL + retries < 3 → retry with feedback
        └── FAIL ≥ 3 → mark hard-fail
"""

import os, re, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.text_metrics import count_metrics
from lib.source_locator import find_source_file
from lib.source_stripper import strip_source_text
from utils import call_api, count_source_chars, get_source_text

PROMPTS_DIR = Path(__file__).parent / "prompts"
AGENT_MODEL = "deepseek-v4-flash"
AGENT_TIMEOUT = 30
AGENT_MAX_TOKENS = 1024


def _load_prompt(name: str, **kwargs) -> str:
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", v)
    return text


def _format_plot_beats(config, ch: int) -> str:
    # Try zero-padded (plot_001.md) first, then unpadded (plot_1.md)
    for fmt in [f"plot_{ch:03d}.md", f"plot_{ch}.md"]:
        guide_path = Path(config["rewrites_dir"]) / "guides" / fmt
        if guide_path.exists():
            text = guide_path.read_text(encoding="utf-8")
            beats = re.search(r"节拍映射表.*?(?=\n##|\Z)", text, re.DOTALL)
            result = beats.group(0) if beats else text
            return result[:1500]  # truncate to keep prompt lean
    return "（无 plot_guide）"


def _format_char_settings(config) -> str:
    s = Path(config["rewrites_dir"]) / "settings" / "characters.md"
    return s.read_text(encoding="utf-8") if s.exists() else "（无设定文件）"


def _strip_names(text: str) -> str:
    return strip_source_text(text)


def _collect_source_summary(config, ch: int) -> str:
    """Collect a brief summary of the source chapter structure (no concrete plot)."""
    text = get_source_text(config, ch)
    if not text:
        return "（源文不可用）"
    chars = len(re.sub(r"\s", "", text))
    lines = len(text.strip().split("\n"))
    return f"源文第{ch}章: {chars}字, {lines}行"


# ── Algorithmic Checks ────────────────────────────

def algorithmic_check(config, ch: int) -> dict:
    """Pure Python checks. Returns metrics + issues."""
    ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return {"pass": False, "issues": ["文件不存在"], "metrics": {}}

    text = ch_file.read_text(encoding="utf-8")
    metrics = count_metrics(text)
    target = count_source_chars(config, ch)

    # 字数
    deviation = (metrics["chars"] - target) / target if target > 0 else 0
    issues = []
    if deviation > 0.20:
        issues.append(f"字数超+{deviation:.0%} ({metrics['chars']}/{target})")
    elif deviation < -0.20:
        issues.append(f"字数不足{deviation:.0%} ({metrics['chars']}/{target})")
    elif abs(deviation) > 0.10:
        issues.append(f"字数偏差{deviation:+.0%} ({metrics['chars']}/{target})")

    # 对话占比 (match any quote style: ASCII "", Chinese "", '', etc.)
    clean_body = re.sub(r"\s", "", text)
    dialog_chars = 0
    for m in re.finditer(r'["""''「」『』]([^""''「」『』]+)["""''「」『』]', text):
        dialog_chars += len(re.sub(r'\s', '', m.group(1)))
    body_len = len(clean_body)
    dialog_ratio = dialog_chars / body_len if body_len else 0

    # 段落数
    paras = [p for p in text.strip().split("\n\n") if p.strip()]

    return {
        "pass": len(issues) == 0,
        "issues": issues,
        "metrics": {
            "chars": metrics["chars"],
            "target": target,
            "deviation": round(deviation, 3),
            "dialog_ratio": round(dialog_ratio, 3),
            "paragraphs": len(paras),
            "metaphor": metrics["metaphor"],
            "ai_markers": metrics["ai_markers"],
        },
    }


# ── Agent Dispatcher ──────────────────────────────

def _run_agent(api_key: str, prompt_name: str, prompt_vars: dict, system: str = "") -> dict:
    prompt = _load_prompt(prompt_name, **prompt_vars)
    try:
        raw = call_api(
            api_key=api_key,
            model=AGENT_MODEL,
            user_prompt=prompt,
            system_prompt=system or None,
            max_tokens=AGENT_MAX_TOKENS,
            reasoning_effort="low",
            temperature=0.1,
            max_retries=1,
        )
        # extract JSON from response - find first { to last }
        json_start = raw.find("{")
        json_end = raw.rfind("}")
        if json_start >= 0 and json_end > json_start:
            json_str = raw[json_start:json_end+1]
            # strip trailing commas before ] and } (common LLM error)
            json_str = re.sub(r',\s*([\]\}])', r'\1', json_str)
            return json.loads(json_str)
        return {"error": "no JSON in response", "raw_preview": raw[:300]}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}", "raw_preview": raw[:300]}
    except Exception as e:
        return {"error": str(e)}


def agent_checks(config, ch: int, api_key: str) -> dict:
    """Launch 4 parallel agents. Returns dict of agent_name → result."""
    ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
    chapter_text = ch_file.read_text(encoding="utf-8") if ch_file.exists() else ""

    # Strip chapter names for peeling audit
    chapter_stripped = _strip_names(chapter_text)

    common_vars = {
        "chapter_text": chapter_text,
        "chapter_stripped": chapter_stripped,
        "plot_beats": _format_plot_beats(config, ch),
        "char_settings": _format_char_settings(config),
        "source_summary": _collect_source_summary(config, ch),
    }

    agents = {
        "beat_audit": {
            "prompt": "beat_audit.md",
            "vars": {k: common_vars[k] for k in ("chapter_text", "plot_beats")},
        },
        "content_audit": {
            "prompt": "content_audit.md",
            "vars": {"chapter_text": chapter_text},
        },
        "peeling_audit": {
            "prompt": "peeling_audit.md",
            "vars": {k: common_vars[k] for k in ("chapter_stripped", "source_summary")},
        },
        "character_audit": {
            "prompt": "character_audit.md",
            "vars": {k: common_vars[k] for k in ("chapter_text", "char_settings")},
        },
    }

    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(_run_agent, api_key, cfg["prompt"], cfg["vars"]): name
            for name, cfg in agents.items()
        }
        for f in as_completed(futures):
            name = futures[f]
            try:
                results[name] = f.result(timeout=AGENT_TIMEOUT)
            except Exception as e:
                results[name] = {"error": str(e), "pass": False}

    # retry failed agents once
    retries = {n: cfg for n, cfg in agents.items()
               if n in results and "error" in results[n]}
    if retries:
        with ThreadPoolExecutor(max_workers=len(retries)) as ex:
            futures = {
                ex.submit(_run_agent, api_key, cfg["prompt"], cfg["vars"]): name
                for name, cfg in retries.items()
            }
            for f in as_completed(futures):
                name = futures[f]
                try:
                    results[name] = f.result(timeout=AGENT_TIMEOUT)
                except Exception as e:
                    results[name] = {"error": str(e), "pass": False}

    return results


# ── Gatekeeper ────────────────────────────────────

def gatekeeper(algo: dict, agents: dict, ch: int) -> dict:
    """Aggregate all checks. Return pass/fail with full report."""

    all_issues = list(algo.get("issues", []))

    # Collect agent issues
    for name, result in agents.items():
        if "error" in result:
            all_issues.append(f"[{name}] agent error: {result['error']}")
            continue
        for issue in result.get("issues", []):
            all_issues.append(f"[{name}] {issue}")

    # Determine pass/fail
    agent_pass = all(
        result.get("pass", False) if "error" not in result else False
        for result in agents.values()
    )
    algo_pass = algo.get("pass", False)
    passed = algo_pass and agent_pass

    return {
        "ch": ch,
        "pass": passed,
        "issues": all_issues,
        "algo": algo,
        "agents": agents,
    }


# ── Public API ────────────────────────────────────

def check_chapter(config, ch: int, api_key: str) -> dict:
    """Run full quality gate on one chapter. Returns gatekeeper report."""
    algo = algorithmic_check(config, ch)
    agents = agent_checks(config, ch, api_key)
    return gatekeeper(algo, agents, ch)


def check_chapters(config, start: int, end: int, api_key: str, workers: int = 10) -> list[dict]:
    """Run quality gate on chapter range. Returns list of reports."""
    results = []
    ch_list = list(range(start, end + 1))

    with ThreadPoolExecutor(max_workers=min(workers, 10)) as ex:
        futures = {ex.submit(check_chapter, config, ch, api_key): ch for ch in ch_list}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"ch": ch, "pass": False, "issues": [str(e)], "algo": {}, "agents": {}})

    results.sort(key=lambda r: r["ch"])
    return results
