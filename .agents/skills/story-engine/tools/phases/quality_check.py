"""Phase 3.3: Quality Gate — algorithmic + multi-agent checks after write.

Usage:
  Directly called from pipeline after write phase.
  Or standalone: pipeline.py --config xxx.json --phase quality_check --start 1 --end 10
"""

import os, time, json
from pathlib import Path
from quality.engine import check_chapters, check_chapter

REPORT_FILE = "quality_report.json"


def phase_quality_check(config, start=1, end=None, workers=10, api_key=None):
    """Run quality gate on chapters. Returns list of chapter reports."""
    api_key = api_key or config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] No API key available")
        return []

    print(f"\n{'=' * 50}")
    print(f"Phase 3.3: Quality Gate (ch{start}-{end or 999}, {workers}w)")
    print("=" * 50)

    t0 = time.time()
    results = check_chapters(config, start, end or 999, api_key, workers)
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
