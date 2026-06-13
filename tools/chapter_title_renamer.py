"""
章节名重命名 — 写 chapter_names.txt，不改正文文件。

核心函数: rename_titles(config, start, end) → {章号: 新标题}

Usage:
    from chapter_title_renamer import rename_titles
    rename_titles(config, 1, 10)

    python tools/chapter_title_renamer.py configs/xxx.json --start 1 --end 10
    python tools/chapter_title_renamer.py configs/xxx.json --start 1 --end 10 --dry-run
"""

import os
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


# ============================================================
# 源文标题
# ============================================================

def find_source_dir(config):
    author = config.get('author', '')
    source_book = config.get('source_book', '')
    base_dir = config.get('base_dir', '.')
    for pat in [f"projects/{author}/{source_book}/源文/", f"projects/{author}/{source_book}/_cache/chapters/"]:
        full = os.path.join(base_dir, pat)
        if os.path.isdir(full) and any(f.endswith('.txt') for f in os.listdir(full)):
            return full
    return None


def extract_source_titles(src_dir):
    """返回 {章号: 标题文本}。"""
    titles = {}
    for f in sorted(Path(src_dir).glob("第*章*.txt"),
                    key=lambda x: int(re.search(r'(\d+)', x.stem).group(1))):
        try:
            text = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = f.read_text(encoding='utf-8-sig')
        first_line = text.strip().split('\n')[0].strip()
        m = re.match(r'第(\d+)章\s*(.*)', first_line)
        if m and m.group(2).strip():
            titles[int(m.group(1))] = m.group(2).strip()
    return titles


# ============================================================
# 当前仿写章节
# ============================================================

def find_chapters_dir(config):
    base = config.get('rewrites_dir', '')
    for d in [os.path.join(base, 'chapters'), os.path.join(base, 'export')]:
        if os.path.isdir(d) and any(f.endswith('.txt') for f in os.listdir(d)):
            return d
    return None


def _find_chapter_file(chapters_dir, ch_num):
    for name in [f"ch_{ch_num:03d}.txt", f"ch_{ch_num}.txt", f"第{ch_num}章.txt"]:
        p = Path(chapters_dir) / name
        if p.exists():
            return p
    return None


def get_current_titles(config, start, end):
    """读取 chapter_names.txt 或从正文提取当前标题。返回 {章号: 标题}。"""
    rewrites_dir = config.get('rewrites_dir', '')
    names_file = os.path.join(rewrites_dir, 'chapter_names.txt')

    # 优先从 chapter_names.txt 读
    if os.path.exists(names_file):
        titles = {}
        for line in Path(names_file).read_text(encoding='utf-8').strip().split('\n'):
            m = re.match(r'第(\d+)章\s*[：:]\s*(.+)', line.strip())
            if not m:
                m = re.match(r'第(\d+)章\s+(.+)', line.strip())
            if m:
                ch = int(m.group(1))
                if start <= ch <= end:
                    titles[ch] = m.group(2).strip()
        if titles:
            return titles

    # fallback: 从正文第一行提取
    chapters_dir = find_chapters_dir(config)
    if not chapters_dir:
        return {}

    titles = {}
    for ch in range(start, end + 1):
        fpath = _find_chapter_file(chapters_dir, ch)
        if fpath:
            first_line = fpath.read_text(encoding='utf-8').strip().split('\n')[0].strip()
            m = re.match(r'第\d+章\s*(.*)', first_line)
            if m and m.group(1).strip():
                titles[ch] = m.group(1).strip()
            else:
                titles[ch] = f"第{ch}章"
    return titles


# ============================================================
# LLM 生成
# ============================================================

def _build_prompt(source_titles, current_titles, config):
    src_lines = [f"第{ch}章 {t}" for ch, t in sorted(source_titles.items())]
    cur_lines = [f"第{ch}章 {t}" for ch, t in sorted(current_titles.items())]

    src_lengths = [len(t) for t in source_titles.values()]
    avg_len = round(sum(src_lengths) / len(src_lengths), 1) if src_lengths else 0
    q_count = sum(1 for t in source_titles.values() if '？' in t)
    e_count = sum(1 for t in source_titles.values() if '……' in t)

    concept = ""
    concept_file = os.path.join(config.get('rewrites_dir', ''), 'concept.md')
    if os.path.exists(concept_file):
        concept = Path(concept_file).read_text(encoding='utf-8')[:500]

    return f"""你是网文章节名专家。为仿写书生成与源文风格一致的章节名。

## 源文章节名（{len(source_titles)}章，平均{avg_len}字，问句{q_count}个，省略句{e_count}个）

{chr(10).join(src_lines)}

## 当前仿写章节（需要你起名的）

{chr(10).join(cur_lines)}

## 设定

{concept}

## 规则

1. 长度：与源文平均长度一致（±2字）
2. 句式：问句/省略句/感叹句的比例与源文一致
3. 称呼词：如有亲昵称呼（宝贝/宝宝/乖宝等），保持源文风格
4. 语气：与源文基调一致（甜/虐/欲/撩/冲突）
5. 内容：反映该章核心冲突或情绪
6. 禁止：源文人名地名、AI味表达（"从XX到XX""他自XX来"）

## 输出

严格按以下格式，每行一个，不要加任何解释：

第1章 标题
第2章 标题
第3章 标题"""


def _parse_llm_output(text, expected_chapters):
    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'第(\d+)章\s*[：:]\s*(.+)', line)
        if not m:
            m = re.match(r'第(\d+)章\s+(.+)', line)
        if m:
            ch = int(m.group(1))
            title = re.sub(r'^[#*_`]+|[#*_`]+$', '', m.group(2)).strip()
            if ch in expected_chapters and title:
                result[ch] = title
    return result


def generate_titles(config, start, end, source_titles, current_titles):
    from lib.api_client import call_api, get_api_url

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("  [ERROR] 未设置 API_KEY")
        return {}

    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")
    prompt = _build_prompt(source_titles, current_titles, config)
    expected = set(range(start, end + 1))

    for attempt in range(3):
        if attempt > 0:
            print(f"  [RETRY] 第{attempt}次重试...")

        try:
            result = call_api(
                api_key, model, prompt,
                reasoning_effort="low", max_tokens=4096, temperature=0.9,
                system_prompt="你是网文章节名专家。只输出「第N章 标题」格式，不加任何解释。",
                api_url=api_url
            )
        except Exception as e:
            print(f"  [ERROR] API 调用失败: {e}")
            continue

        new_titles = _parse_llm_output(result, expected)
        coverage = len(new_titles) / len(expected) if expected else 0
        if coverage >= 0.8:
            print(f"  [OK] 生成 {len(new_titles)}/{len(expected)} 个标题 ({coverage:.0%})")
            return new_titles
        else:
            print(f"  [WARN] 覆盖率不足: {len(new_titles)}/{len(expected)} ({coverage:.0%})")

    return new_titles if new_titles else {}


# ============================================================
# 写入 chapter_names.txt + 章节文件
# ============================================================

def _replace_title_in_file(chapter_file, new_title):
    """替换章节文件第一行标题。"""
    text = chapter_file.read_text(encoding='utf-8')
    lines = text.strip().split('\n')

    if lines and re.match(r'第\d+章', lines[0]):
        lines[0] = new_title
    else:
        lines.insert(0, new_title)
        lines.insert(1, '')

    chapter_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def save_chapter_names(config, new_titles, dry_run=False):
    """写入 chapter_names.txt + 更新章节文件第一行。"""
    rewrites_dir = config.get('rewrites_dir', '')

    # --- 1. chapter_names.txt ---
    names_file = os.path.join(rewrites_dir, 'chapter_names.txt')
    existing = {}
    if os.path.exists(names_file):
        for line in Path(names_file).read_text(encoding='utf-8').strip().split('\n'):
            m = re.match(r'第(\d+)章\s*[：:]\s*(.+)', line.strip())
            if not m:
                m = re.match(r'第(\d+)章\s+(.+)', line.strip())
            if m:
                existing[int(m.group(1))] = m.group(2).strip()

    existing.update(new_titles)

    if not dry_run:
        lines = [f"第{ch}章 {title}" for ch, title in sorted(existing.items())]
        Path(names_file).write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f"  chapter_names.txt: {len(lines)} 章")

    # --- 2. 章节文件第一行 ---
    chapters_dir = find_chapters_dir(config)
    if not chapters_dir:
        print("  [WARN] 未找到章节目录，只更新了 chapter_names.txt")
        return len(new_titles)

    applied = 0
    for ch_num, title in sorted(new_titles.items()):
        fpath = _find_chapter_file(chapters_dir, ch_num)
        if not fpath:
            continue

        full_title = f"第{ch_num}章 {title}"
        if dry_run:
            print(f"  [DRY] {fpath.name}: → {full_title}")
        else:
            _replace_title_in_file(fpath, full_title)
        applied += 1

    if not dry_run:
        print(f"  章节文件: 更新 {applied} 个")

    return applied


# ============================================================
# 主函数
# ============================================================

def rename_titles(config, start, end, dry_run=False):
    """章节名重命名全流程。返回 {章号: 新标题}。"""
    print(f"\n{'=' * 50}")
    print(f"章节名重命名 (ch{start}-{end})")
    print("=" * 50)

    # 1. 源文标题
    src_dir = find_source_dir(config)
    if not src_dir:
        print("  [SKIP] 未找到源文目录")
        return {}

    source_titles = extract_source_titles(src_dir)
    if not source_titles:
        print("  [SKIP] 源文无标题")
        return {}
    avg_len = round(sum(len(t) for t in source_titles.values()) / len(source_titles), 1)
    print(f"  源文: {len(source_titles)} 章, 平均 {avg_len} 字")

    # 2. 当前仿写标题
    current_titles = get_current_titles(config, start, end)
    print(f"  仿写: {len(current_titles)} 章待命名")

    # 3. LLM 生成
    new_titles = generate_titles(config, start, end, source_titles, current_titles)
    if not new_titles:
        print("  [FAIL] 生成失败")
        return {}

    # 4. 保存
    if dry_run:
        print("\n  [DRY RUN] 预览:")
        for ch in sorted(new_titles.keys()):
            old = current_titles.get(ch, "(无)")
            print(f"    {old} → 第{ch}章 {new_titles[ch]}")
    else:
        save_chapter_names(config, new_titles)

    print(f"\n  完成！{len(new_titles)} 个标题")
    return new_titles


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='章节名重命名')
    parser.add_argument('config', help='配置文件路径')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=999)
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    config.setdefault('base_dir', os.getcwd())

    if args.end == 999:
        from utils import get_chapters_list
        chs = get_chapters_list(config)
        if chs:
            args.end = max(chs)

    rename_titles(config, args.start, args.end, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
