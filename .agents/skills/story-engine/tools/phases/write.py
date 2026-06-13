"""Phase 3: 写章（含 JIT guide 自动生成，不再依赖 guides phase 预生成）"""

import os
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import count_source_chars, batch_run


def _expand_one(config, ch, target_ratio=1.3):
    """扩写单章：字数不够时调用，不重写整章。"""
    from lib.api_client import call_api, get_api_url
    from prompt_loader import load_prompt_str, get_prompt_config_with_overrides

    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    ch_file = chapters_dir / f"ch_{ch:03d}.txt"
    original = ch_file.read_text(encoding='utf-8')
    orig_chars = len(original.replace('\n', '').replace(' ', ''))
    target_chars = int(orig_chars * target_ratio)

    prompt_template = load_prompt_str("expand-chapter.md")
    r = {"content": original, "orig_chars": orig_chars, "target_chars": target_chars,
         "min_chars": int(target_chars * 0.9), "max_chars": int(target_chars * 1.1)}
    prompt = prompt_template.format(**r)

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    pc = get_prompt_config_with_overrides("expand-chapter.md", config)
    result = call_api(api_key, pc.get("model", config.get("model")), prompt,
                      reasoning_effort=pc.get("reasoning_effort", "low"),
                      max_tokens=pc.get("max_tokens", 10000),
                      temperature=pc.get("temperature", 0.8),
                      system_prompt="", api_url=get_api_url(config))
    ch_file.write_text(result.strip(), encoding='utf-8')


def _trim_one(config, ch):
    """精索单章：字数超了时调用，不重写整章。"""
    from phases.guides import run_one

    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    ch_file = chapters_dir / f"ch_{ch:03d}.txt"
    text = ch_file.read_text(encoding='utf-8')
    lines = text.strip().split('\n')
    title = lines[0] if lines and lines[0].startswith('第') else f"第{ch}章"

    result = run_one(config, "trim-chapter", ch)
    ch_file.write_text(title + '\n\n' + result.strip(), encoding='utf-8')


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


def _ensure_style_guides(config, start, end, workers=10):
    """JIT: 写章前自动生成缺失的 style_guide。"""
    from phases.guides import run_one as guide_run_one
    from state_manager import atomic_write_text

    guides_dir = Path(config["rewrites_dir"]) / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for ch in range(start, end + 1):
        style_file = guides_dir / f"style_{ch}.md"
        if not style_file.exists() or style_file.stat().st_size < 50:
            missing.append(ch)

    if not missing:
        return

    print(f"  [JIT] 自动生成 {len(missing)} 个缺失 style_guide: ch{min(missing)}-{max(missing)}")
    t0 = time.time()
    ok_count = 0

    with ThreadPoolExecutor(max_workers=min(workers, len(missing), 50)) as ex:
        futures = {ex.submit(guide_run_one, config, "style-guide", ch): ch for ch in missing}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                result = f.result()
                atomic_write_text(guides_dir / f"style_{ch}.md", result)
                ok_count += 1
            except Exception as e:
                print(f"  [JIT] ch{ch} style-guide ✗: {e}")

    print(f"  [JIT] style_guide: {ok_count}/{len(missing)} 完成 ({time.time()-t0:.0f}s)")


def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 异常章自动重跑 + JIT guide 自动生成。"""
    from phases.guides import run_one

    # Step 0: JIT 生成缺失 plot_guide + style_guide（只对要写的章，不浪费）
    _ensure_plot_guides(config, start, end, workers)
    _ensure_style_guides(config, start, end, workers)

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

    # 按需修正字数：少→expand，多→trim，不重写
    for fix_round in range(1, 3):
        fix_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            target = count_source_chars(config, ch)
            chars = len(re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text))
            if target > 0:
                ratio = chars / target
                if ratio < 0.7:
                    fix_list.append((ch, "expand", chars, target))
                elif ratio > 1.3:
                    fix_list.append((ch, "trim", chars, target))
            elif chars < 500:
                fix_list.append((ch, "expand", chars, 0))

        if not fix_list:
            break

        for ch, action, chars, target in fix_list:
            print(f"  [{action.upper()}] ch{ch:03d}: {chars}字 → 目标{target}字")
            try:
                from phases.write import _expand_one, _trim_one
                if action == "expand":
                    _expand_one(config, ch, target_ratio=1.3)
                else:
                    _trim_one(config, ch)
            except Exception as e:
                print(f"  [FAIL] {action} ch{ch}: {e}")

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



