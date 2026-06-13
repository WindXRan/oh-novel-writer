"""Phase 3.3: Quality Gate — algorithmic + multi-agent checks after write.

Self-healing: failed chapters are retried with quality feedback injected
into the rewrite prompt. Max 2 retries per chapter.
"""

import os, time, json
from pathlib import Path
from quality.engine import check_chapters, check_chapter

REPORT_FILE = "quality_report.json"
MAX_RETRIES = 2
RETRY_MODEL = "deepseek-v4-pro"


def _format_feedback(issues: list) -> str:
    """Format quality issues as feedback string for extra_replacements."""
    top = issues[:5]
    lines = []
    for iss in top:
        lines.append(f"- {iss}")
    return "\n".join(lines)


def _rewrite_chapter(config, ch: int, feedback: str = ""):
    """Re-run write-chapter prompt for one chapter with feedback injection."""
    from phases.guides import run_one
    extra = {}
    if feedback:
        extra["质量反馈"] = f"\n## 上一版的问题（本次必须修复）\n{feedback}\n"
    run_one(config, "write-chapter", ch, model=RETRY_MODEL, extra_replacements=extra)


def _retry_failed(config, results, api_key, workers):
    """Retry failed chapters with quality feedback injection."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    for attempt in range(1, MAX_RETRIES + 1):
        failed = [r for r in results if not r["pass"]]
        if not failed:
            break

        print(f"\n  [RETRY {attempt}/{MAX_RETRIES}] {len(failed)} 章重写中...")

        # Rewrite all failed chapters in parallel
        with ThreadPoolExecutor(max_workers=min(workers, 10)) as ex:
            futures = {}
            for r in failed:
                feedback = _format_feedback(r["issues"])
                futures[ex.submit(_rewrite_chapter, config, r["ch"], feedback)] = r["ch"]
            for f in as_completed(futures):
                ch = futures[f]
                try:
                    f.result()
                except Exception as e:
                    print(f"    ch{ch:03d} rewrite error: {e}")

        # Re-check all rewritten chapters
        rechecked = {}
        with ThreadPoolExecutor(max_workers=min(workers, 10)) as ex:
            futures = {ex.submit(check_chapter, config, r["ch"], api_key): r["ch"] for r in failed}
            for f in as_completed(futures):
                ch = futures[f]
                try:
                    rechecked[ch] = f.result()
                except Exception as e:
                    rechecked[ch] = {"ch": ch, "pass": False, "issues": [str(e)], "algo": {}, "agents": {}}

        for i, r in enumerate(results):
            if r["ch"] in rechecked:
                results[i] = rechecked[r["ch"]]

        passed_r = [r for r in results if r["pass"]]
        failed_r = [r for r in results if not r["pass"]]
        print(f"  [RETRY RESULT] PASS={len(passed_r)} FAIL={len(failed_r)}")

    return results


def phase_quality_check(config, start=1, end=None, workers=10, api_key=None):
    """Run quality gate on chapters. Self-heals failed chapters."""
    api_key = api_key or config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] No API key available")
        return []

    print(f"\n{'=' * 50}")
    print(f"Phase 3.3: Quality Gate (ch{start}-{end or 999}, {workers}w, max_retry={MAX_RETRIES})")
    print("=" * 50)

    t0 = time.time()
    results = check_chapters(config, start, end or 999, api_key, workers)
    results = _retry_failed(config, results, api_key, workers)
    elapsed = time.time() - t0

    # Print summary
    passed = [r for r in results if r["pass"]]
    failed = [r for r in results if not r["pass"]]
    errored = [r for r in failed if "error" in str(r.get("issues", []))]

    print(f"\nSummary: {len(passed)} PASS | {len(failed)} FAIL ({len(errored)} errors) | {elapsed:.0f}s")

    for r in failed:
        print(f"  ch{r['ch']:03d} FAIL")
        for iss in r["issues"][:5]:
            print(f"    - {iss}")
        if len(r["issues"]) > 5:
            print(f"    ... +{len(r['issues'])-5} more")

    # Save report
    report_path = Path(config["rewrites_dir"]) / "compare" / REPORT_FILE
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n  [REPORT] {report_path}")

    return results
