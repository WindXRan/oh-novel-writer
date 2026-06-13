"""
章节名风格分析器：提取源文章节名 + 统计数据，供 LLM 分析风格用。

Usage:
    python tools/chapter_title_analyzer.py <源文目录> [--output <输出目录>]
    python tools/chapter_title_analyzer.py projects/奶糖酥/酸涩湿吻/源文
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


def extract_titles(src_dir: str) -> list:
    """从源文目录提取所有章节标题。返回 [(章号, 标题文本), ...]"""
    src_path = Path(src_dir)
    titles = []
    
    files = sorted(src_path.glob("第*章*.txt"), 
                   key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)))
    
    for f in files:
        try:
            text = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = f.read_text(encoding='utf-8-sig')
        
        first_line = text.strip().split('\n')[0].strip()
        m = re.match(r'第(\d+)章\s*(.*)', first_line)
        if m:
            ch_num = int(m.group(1))
            title_text = m.group(2).strip()
            titles.append((ch_num, title_text))
        else:
            ch_num = int(re.search(r'(\d+)', f.stem).group(1))
            titles.append((ch_num, first_line))
    
    return titles


def compute_stats(titles: list) -> dict:
    """计算章节名的基础统计数据（纯数值，不做风格判断）。"""
    title_texts = [t[1] for t in titles if t[1]]
    if not title_texts:
        return {"error": "无有效标题"}
    
    lengths = [len(t) for t in title_texts]
    
    # 标点统计
    question_count = sum(1 for t in title_texts if '？' in t or '?' in t)
    ellipsis_count = sum(1 for t in title_texts if '……' in t or '...' in t)
    exclamation_count = sum(1 for t in title_texts if '！' in t or '!' in t)
    period_count = sum(1 for t in title_texts if t.endswith('。'))
    
    # 人称统计
    first_person = sum(1 for t in title_texts if '我' in t)
    second_person = sum(1 for t in title_texts if '你' in t)
    
    return {
        "total_chapters": len(title_texts),
        "avg_length": round(sum(lengths) / len(lengths), 1),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "length_distribution": {
            "1-2字": sum(1 for l in lengths if l <= 2),
            "3-4字": sum(1 for l in lengths if 3 <= l <= 4),
            "5-6字": sum(1 for l in lengths if 5 <= l <= 6),
            "7-8字": sum(1 for l in lengths if 7 <= l <= 8),
            "9字+": sum(1 for l in lengths if l >= 9),
        },
        "punctuation": {
            "问号？": question_count,
            "省略号……": ellipsis_count,
            "感叹号！": exclamation_count,
            "句号。": period_count,
        },
        "pronouns": {
            "含'我'": first_person,
            "含'你'": second_person,
        },
    }


def main():
    parser = argparse.ArgumentParser(description='章节名风格分析器')
    parser.add_argument('src_dir', help='源文目录路径')
    parser.add_argument('--output', '-o', help='输出目录（默认：源文目录的父目录/style_analysis）')
    
    args = parser.parse_args()
    
    src_dir = Path(args.src_dir)
    if not src_dir.exists():
        print(f"错误：目录不存在 {src_dir}")
        sys.exit(1)
    
    # 提取标题
    print(f"提取章节标题: {src_dir}")
    titles = extract_titles(str(src_dir))
    if not titles:
        print("错误：未找到章节")
        sys.exit(1)
    print(f"  找到 {len(titles)} 个章节")
    
    # 计算统计
    stats = compute_stats(titles)
    
    # 确定输出目录
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = src_dir.parent / "style_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存标题列表（纯文本，每行一个，供 LLM 消费）
    titles_text = '\n'.join(f"第{ch}章 {title}" for ch, title in titles)
    titles_file = out_dir / "source_titles.txt"
    titles_file.write_text(titles_text, encoding='utf-8')
    print(f"  标题列表: {titles_file}")
    
    # 保存统计数据（JSON）
    stats_file = out_dir / "title_stats.json"
    stats_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  统计数据: {stats_file}")
    
    print(f"\n完成！平均长度: {stats['avg_length']}字, 问句: {stats['punctuation']['问号？']}章")


if __name__ == '__main__':
    main()
