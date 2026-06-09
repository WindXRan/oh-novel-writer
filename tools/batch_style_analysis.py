"""批量分析源文章节风格，输出每章独立的风格指标 JSON（参考 inkos style-analyzer）"""
import re
import sys
import json
import os
from pathlib import Path
from collections import Counter

# 设置stdout为UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

# 修辞模式（参考 inkos style-analyzer.ts）
RHETORICAL_PATTERNS = [
    {"name": "比喻(像/如/仿佛)", "regex": r"(?:像|如|仿佛|似)(?:是|同|一般|一样)"},
    {"name": "排比", "regex": r"[，。；]([^，。；]{2,6})[，。；]\1"},
    {"name": "反问", "regex": r"难道|怎么可能|岂不是|何尝不"},
    {"name": "夸张", "regex": r"天崩地裂|惊天动地|翻天覆地|震耳欲聋"},
    {"name": "拟人", "regex": r"[风雨雪月花树草石](?:在|像|仿佛).*?(?:笑|哭|叹|呻|吟|怒|舞)"},
]


def extract_metrics(text):
    """提取源文风格指标（每章独立，参考 inkos style-analyzer）"""
    clean = re.sub(r'\s', '', text)
    total_chars = len(clean)
    
    # 分句（按句号、问号、感叹号、换行分）
    sentences = re.split(r'[。！？\n]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    total_sentences = len(sentences)
    
    # 句子长度统计
    sentence_lengths = [len(re.sub(r'\s', '', s)) for s in sentences]
    avg_sentence_len = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    sentence_len_std = 0
    if len(sentence_lengths) > 1:
        mean = avg_sentence_len
        variance = sum((x - mean) ** 2 for x in sentence_lengths) / len(sentence_lengths)
        sentence_len_std = variance ** 0.5
    
    # 段落统计（按空行分段）
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.strip()) > 5]
    paragraph_lengths = [len(p) for p in paragraphs]
    avg_paragraph_len = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
    min_paragraph = min(paragraph_lengths) if paragraph_lengths else 0
    max_paragraph = max(paragraph_lengths) if paragraph_lengths else 0
    
    # 单句段占比（只有一个句号的段落）
    single_sentence_paras = sum(1 for p in paragraphs if len(re.findall(r'[。！？]', p)) <= 1)
    single_para_ratio = single_sentence_paras / len(paragraphs) * 100 if paragraphs else 0
    
    # 对话占比
    dialogue_chars = 0
    for match in re.finditer(r'\u201c([^\u201d]*)\u201d', text):
        dialogue_chars += len(re.sub(r'\s', '', match.group(1)))
    dialogue_ratio = dialogue_chars / total_chars * 100 if total_chars > 0 else 0
    
    # 短句/长句占比
    short_sentences = sum(1 for s in sentences if len(re.sub(r'\s', '', s)) <= 15)
    long_sentences = sum(1 for s in sentences if len(re.sub(r'\s', '', s)) >= 30)
    short_ratio = short_sentences / total_sentences * 100 if total_sentences > 0 else 0
    long_ratio = long_sentences / total_sentences * 100 if total_sentences > 0 else 0
    
    # 词汇多样性 (TTR - Type-Token Ratio)
    chars = re.sub(r'[\s\n\r，。！？、：；""''（）【】《》0-9]', '', text)
    unique_chars = set(chars)
    vocabulary_diversity = len(unique_chars) / len(chars) if chars else 0
    
    # 句首模式（前2个字符）
    opening_counts = {}
    for s in sentences:
        if len(s) >= 2:
            opening = s[:2]
            opening_counts[opening] = opening_counts.get(opening, 0) + 1
    top_patterns = sorted(opening_counts.items(), key=lambda x: -x[1])[:5]
    top_patterns = [f"{p}...({c}次)" for p, c in top_patterns if c >= 3]
    
    # 修辞特征
    rhetorical_features = []
    for pattern in RHETORICAL_PATTERNS:
        matches = re.findall(pattern["regex"], text)
        if len(matches) >= 2:
            rhetorical_features.append(f"{pattern['name']}({len(matches)}处)")
    
    # 比喻句数量（含像/仿佛/犹如/恍如）
    simile_count = len(re.findall(r'(?:像|仿佛|犹如|恍如)', text))
    
    # AI路标词
    ai_markers = ['首先', '其次', '然后', '最后', '与此同时', '值得注意的是', '此外']
    ai_marker_count = sum(text.count(w) for w in ai_markers)
    
    # 直抒情词
    direct_emotion = ['充满了', '感到无比', '心中涌起', '不由得', '不禁']
    direct_emotion_count = sum(text.count(w) for w in direct_emotion)
    
    # 省略号数量
    ellipsis_count = text.count('……') + text.count('...')
    
    return {
        "total_chars": total_chars,
        "total_sentences": total_sentences,
        "avg_sentence_len": round(avg_sentence_len, 1),
        "sentence_len_std": round(sentence_len_std, 1),
        "avg_paragraph_len": round(avg_paragraph_len),
        "paragraph_len_range": {"min": min_paragraph, "max": max_paragraph},
        "single_para_ratio": round(single_para_ratio, 1),
        "dialogue_ratio": round(dialogue_ratio, 1),
        "short_ratio": round(short_ratio, 1),
        "long_ratio": round(long_ratio, 1),
        "vocabulary_diversity": round(vocabulary_diversity, 3),
        "top_patterns": top_patterns,
        "rhetorical_features": rhetorical_features,
        "simile_count": simile_count,
        "ai_marker_count": ai_marker_count,
        "direct_emotion_count": direct_emotion_count,
        "ellipsis_count": ellipsis_count,
    }


def batch_analyze(src_dir, output_dir):
    """批量分析所有章节"""
    src_path = Path(src_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 按章节号排序
    files = sorted(src_path.glob("第*章.txt"), key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)))
    
    if not files:
        print(f"未找到章节文件: {src_dir}")
        return
    
    all_metrics = []
    
    for f in files:
        chapter_num = re.search(r'(\d+)', f.stem).group(1)
        text = f.read_text(encoding='utf-8')
        metrics = extract_metrics(text)
        metrics['chapter'] = int(chapter_num)
        metrics['file'] = f.name
        
        # 保存单章 JSON
        out_file = out_path / f"style_{chapter_num}.json"
        with open(out_file, 'w', encoding='utf-8') as fout:
            json.dump(metrics, fout, ensure_ascii=False, indent=2)
        
        all_metrics.append(metrics)
    
    # 保存汇总
    summary_file = out_path / "all_chapters_style.json"
    with open(summary_file, 'w', encoding='utf-8') as fout:
        json.dump(all_metrics, fout, ensure_ascii=False, indent=2)
    
    # 打印统计摘要
    print(f"已分析 {len(files)} 章，输出到: {output_dir}")
    print(f"\n--- 汇总统计 ---")
    
    # 计算各项指标的均值和范围
    for key in ['total_chars', 'avg_sentence_len', 'sentence_len_std', 'avg_paragraph_len',
                'dialogue_ratio', 'short_ratio', 'long_ratio', 'single_para_ratio', 
                'vocabulary_diversity', 'simile_count', 'ai_marker_count', 
                'direct_emotion_count', 'ellipsis_count']:
        values = [m[key] for m in all_metrics]
        mean = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        print(f"{key}: 均值={mean:.1f}, 范围=[{min_val}, {max_val}]")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python batch_style_analysis.py <源文目录> <输出目录>")
        print("Example: python batch_style_analysis.py projects/奶糖酥/酸涩湿吻/源文 projects/奶糖酥/酸涩湿吻/style_analysis")
        sys.exit(1)
    
    batch_analyze(sys.argv[1], sys.argv[2])
