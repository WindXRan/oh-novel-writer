"""Phase 3: 写章（含 JIT guide 自动生成，不再依赖 guides phase 预生成）"""

import os
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import count_source_chars, batch_run


def _ensure_plot_guides(config, start, end, workers=10):
    """JIT: 写章前自动生成缺失的 plot_guide。
    
    核心优化：guides 不再提前生成一大片。只生成即将写章的那些，0 浪费。
    """
    from phases.guides import run_one as guide_run_one, process_plot_guide_output
    from state_manager import atomic_write_text

    guides_dir = Path(config["rewrites_dir"]) / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for ch in range(start, end + 1):
        plot_file = guides_dir / f"plot_{ch}.md"
        if not plot_file.exists() or plot_file.stat().st_size < 50:
            missing.append(ch)

    if not missing:
        return

    print(f"  [JIT] 自动生成 {len(missing)} 个缺失 plot_guide: ch{min(missing)}-{max(missing)}")
    t0 = time.time()
    ok_count = 0

    with ThreadPoolExecutor(max_workers=min(workers, len(missing), 50)) as ex:
        futures = {ex.submit(guide_run_one, config, "plot-guide", ch): ch for ch in missing}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                result = f.result()
                result = process_plot_guide_output(config, ch, result)
                atomic_write_text(guides_dir / f"plot_{ch}.md", result)
                ok_count += 1
            except Exception as e:
                print(f"  [JIT] ch{ch} plot-guide ✗: {e}")

    print(f"  [JIT] plot_guide: {ok_count}/{len(missing)} 完成 ({time.time()-t0:.0f}s)")


def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 异常章自动重跑 + JIT guide 自动生成。"""
    from phases.guides import run_one

    # Step 0: JIT 生成缺失 plot_guide（只对要写的章，不浪费）
    _ensure_plot_guides(config, start, end, workers)

    chapters_dir = f"{config['rewrites_dir']}/chapters"
    write_cfg = {**config}
    model_label = write_cfg.get("model", "default")

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章 (model={model_label}, ch{start}-{end}, {workers}w)")
    print("=" * 50)

    if state_mgr:
        state_mgr.phase_start("write")

    t0 = time.time()
    run_id = None
    if state_mgr:
        run_id = state_mgr.add_run("write", start, end, model=write_cfg.get("model", "deepseek-v4-flash"))

    ok, fail = batch_run(write_cfg, "write-chapter", start, end, workers, chapters_dir,
                         "ch_{ch:03d}.txt", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one)

    for retry_round in range(1, 3):
        retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            target = count_source_chars(config, ch)
            chars = len(re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text))
            if target > 0:
                deviation = abs(chars - target) / target
                if deviation > 0.3:
                    retry_list.append((ch, f"字数{chars}/{target}"))
            elif chars < 500:
                retry_list.append((ch, f"字数{chars}/0(源文缺失)"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章字数异常: {[(c, w) for c,w in retry_list]}")
        for ch, _ in retry_list:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.unlink(missing_ok=True)
            if state_mgr:
                state_mgr.chapter_writing(ch)

        ok2, fail2 = batch_run(write_cfg, "write-chapter",
            min(c for c, _ in retry_list), max(c for c, _ in retry_list),
            workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=False,
            state_mgr=state_mgr, run_one_func=run_one)
        ok.update(ok2)
        fail.update(fail2)

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n', '').replace(' ', '').replace('\r', ''))
        for path in ok.values()
    )
    print(f"  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耗时 {time.time()-t0:.0f}s")

    if state_mgr:
        if fail:
            state_mgr.phase_failed("write", error=f"{len(fail)}章失败")
        else:
            state_mgr.phase_done("write", extra={"total_chars": total})
        if run_id:
            state_mgr.finish_run(run_id, ok=len(ok), fail=len(fail))

    return ok, fail



