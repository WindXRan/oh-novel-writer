"""批量生成每章的 style_guide（脚本提取定量数据 + LLM 生成执行规则）"""
import json
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


def load_style_guide_prompt():
    """加载 style-guide prompt 模板"""
    prompt_path = Path(__file__).parent.parent / ".agents/skills/story-engine/prompts/style-guide.md"
    return prompt_path.read_text(encoding='utf-8')


def generate_style_guide_for_chapter(chapter_num, style_data, src_text, new_book_name, author_name, src_book_name):
    """为单章生成 style_guide prompt"""
    prompt_template = load_style_guide_prompt()
    
    # 构建定量指标文本
    metrics_text = f"""
- 总字数：{style_data['total_chars']}字
- 平均句长：{style_data['avg_sentence_len']}字 | 标准差：{style_data['sentence_len_std']}
- 平均段长：{style_data['avg_paragraph_len']}字
- 段落长度范围：{style_data['paragraph_len_range']['min']}~{style_data['paragraph_len_range']['max']}字
- 短句（≤15字）占比：{style_data['short_ratio']}%
- 长句（≥30字）占比：{style_data['long_ratio']}%
- 对话占比：{style_data['dialogue_ratio']}%
- 单句段占比：{style_data['single_para_ratio']}%
- 词汇多样性 (TTR)：{style_data['vocabulary_diversity']}
- 句首模式：{', '.join(style_data['top_patterns']) if style_data['top_patterns'] else '无'}
- 修辞特征：{', '.join(style_data['rhetorical_features']) if style_data['rhetorical_features'] else '无'}
- 比喻句数量：{style_data['simile_count']}句
- AI路标词出现次数：{style_data['ai_marker_count']}次
- 直抒情出现次数：{style_data['direct_emotion_count']}次
- 省略号数量：{style_data['ellipsis_count']}个
"""
    
    # 替换模板中的变量
    prompt = prompt_template.replace("{新书名}", new_book_name)
    prompt = prompt.replace("{N}", str(chapter_num))
    prompt = prompt.replace("{作者名}", author_name)
    prompt = prompt.replace("{源书名}", src_book_name)
    prompt = prompt.replace("{源文指标}", metrics_text)
    
    # 计算字数范围
    target_chars = style_data['total_chars']
    min_chars = int(target_chars * 0.9)
    max_chars = int(target_chars * 1.1)
    prompt = prompt.replace("{目标字数}", str(target_chars))
    prompt = prompt.replace("{目标字数_min}", str(min_chars))
    prompt = prompt.replace("{目标字数_max}", str(max_chars))
    
    return prompt


def call_llm(prompt, api_key=None):
    """调用 LLM 生成 style_guide"""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key or os.environ.get("API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专业的网文风格分析师，擅长提取源文的写作风格并生成可执行的写作规则。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None


def batch_generate(style_dir, src_dir, output_dir, new_book_name, author_name, src_book_name, api_key=None):
    """批量生成所有章节的 style_guide"""
    style_path = Path(style_dir)
    src_path = Path(src_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 读取所有章节的风格数据
    style_files = sorted(style_path.glob("style_*.json"), key=lambda x: int(x.stem.split('_')[1]))
    
    print(f"找到 {len(style_files)} 个章节的风格数据")
    print(f"开始生成 style_guide...")
    
    success_count = 0
    fail_count = 0
    
    for style_file in style_files:
        chapter_num = int(style_file.stem.split('_')[1])
        
        # 检查是否已存在
        out_file = out_path / f"style_{chapter_num}.md"
        if out_file.exists():
            print(f"跳过第{chapter_num}章（已存在）")
            success_count += 1
            continue
        
        # 读取风格数据
        with open(style_file, 'r', encoding='utf-8') as f:
            style_data = json.load(f)
        
        # 读取源文
        src_file = src_path / f"第{chapter_num}章.txt"
        if not src_file.exists():
            print(f"警告：源文不存在 {src_file}")
            fail_count += 1
            continue
        
        src_text = src_file.read_text(encoding='utf-8')
        
        # 生成 prompt
        prompt = generate_style_guide_for_chapter(
            chapter_num, style_data, src_text, 
            new_book_name, author_name, src_book_name
        )
        
        # 调用 LLM
        print(f"正在生成第{chapter_num}章的 style_guide...")
        result = call_llm(prompt, api_key)
        
        if result:
            # 保存结果
            out_file.write_text(result, encoding='utf-8')
            print(f"✓ 第{chapter_num}章生成完成")
            success_count += 1
        else:
            print(f"✗ 第{chapter_num}章生成失败")
            fail_count += 1
    
    print(f"\n完成！成功: {success_count}, 失败: {fail_count}")
    print(f"输出目录：{output_dir}")


if __name__ == '__main__':
    if len(sys.argv) < 7:
        print("Usage: python batch_gen_style_guides_llm.py <style_analysis目录> <源文目录> <输出目录> <新书名> <作者名> <源书名> [api_key]")
        print("Example: python batch_gen_style_guides_llm.py projects/奶糖酥/酸涩湿吻/style_analysis projects/奶糖酥/酸涩湿吻/源文 projects/奶糖酥/酸涩湿吻/rewrites/酸涩湿吻/guides 酸涩湿吻 奶糖酥 酸涩湿吻")
        sys.exit(1)
    
    api_key = sys.argv[7] if len(sys.argv) > 7 else None
    batch_generate(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], api_key)
