"""根据每章风格 JSON 生成 style_guide.md，写章时注入"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


def generate_style_guide(style_data, output_path):
    """根据风格数据生成 style_guide.md"""
    d = style_data
    
    # 根据数据生成约束
    guide = f"""## 定量锚点（写章后自动校验）

- 总字数：{d['total_chars']}字 → 目标 ±10%（{int(d['total_chars']*0.9)}~{int(d['total_chars']*1.1)}字）
- 平均句长：{d['avg_sentence_len']}字 | 标准差：{d['sentence_len_std']}
- 短句（≤15字）占比：{d['short_ratio']}%
- 长句（≥30字）占比：{d['long_ratio']}%
- 对话占比：{d['dialogue_ratio']}%
- 单句段占比：{d['single_para_ratio']}%
- 比喻句数量：{d['simile_count']}句 → 仿写 ±2
- AI路标词：{d['ai_marker_count']}次 → **仿写必须为0**
- 直抒情：{d['direct_emotion_count']}次 → **仿写必须为0**
- 省略号：{d['ellipsis_count']}个 → 仿写 ±2

## 写作约束

- 句式长短交错，不要连续3句以上都是长句或短句
- 对话要自然口语化，带语气词
- 段落以单句段为主，偶尔用多句段做节奏变化
- 比喻要克制，一章最多2-3个
- 禁止使用 AI 路标词（首先/其次/然后/最后/与此同时/值得注意的是/此外）
- 禁止直抒情（"充满了""感到无比""心中涌起""不由得""不禁"）
- 省略号不要滥用，一章最多5个
"""
    
    Path(output_path).write_text(guide, encoding='utf-8')
    return guide


def batch_generate(style_dir, guides_dir):
    """批量生成所有章节的 style_guide"""
    style_path = Path(style_dir)
    guides_path = Path(guides_dir)
    guides_path.mkdir(parents=True, exist_ok=True)
    
    files = sorted(style_path.glob("style_*.json"), key=lambda x: int(x.stem.split('_')[1]))
    
    for f in files:
        chapter_num = f.stem.split('_')[1]
        with open(f, 'r', encoding='utf-8') as fin:
            style_data = json.load(fin)
        
        out_file = guides_path / f"style_{chapter_num}.md"
        generate_style_guide(style_data, out_file)
    
    print(f"已生成 {len(files)} 个 style_guide，输出到: {guides_dir}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python gen_style_guides.py <style_analysis目录> <guides输出目录>")
        print("Example: python gen_style_guides.py projects/奶糖酥/酸涩湿吻/style_analysis projects/奶糖酥/酸涩湿吻/rewrites/酸涩湿吻/guides")
        sys.exit(1)
    
    batch_generate(sys.argv[1], sys.argv[2])
