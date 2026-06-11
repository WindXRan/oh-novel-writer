"""
模板合并工具：把 AI 输出的 JSON 内容填入模板文件。

用法：
  python template_merger.py --template templates/plot-guide-output.md --content output.json --output plot_1.md
  
  # 在代码中使用
  from template_merger import merge_json_to_template
  result = merge_json_to_template(template_path, json_content)
"""

import json
import re
import argparse
from pathlib import Path


def load_template(template_path):
    """加载模板文件。"""
    return Path(template_path).read_text(encoding='utf-8')


def merge_json_to_template(template_path, json_content):
    """把 JSON 内容填入模板。
    
    Args:
        template_path: 模板文件路径
        json_content: JSON 字典或 JSON 字符串
    
    Returns:
        合并后的文本
    """
    template = load_template(template_path)
    
    # 如果是字符串，解析为字典
    if isinstance(json_content, str):
        json_content = json.loads(json_content)
    
    result = template
    
    # 替换所有占位符
    for key, value in json_content.items():
        # 检查各种可能的占位符格式
        placeholders = [f'{{{key}}}', f'{{{key}_table}}', f'{{{key}_list}}']
        found = False
        for ph in placeholders:
            if ph in result:
                found = True
                break
        
        if not found:
            continue
        
        if isinstance(value, list):
            # 数组类型：根据占位符上下文判断格式
            if f'{{{key}_table}}' in result:
                # 表格行格式
                table_rows = []
                for item in value:
                    if isinstance(item, dict):
                        row = "| " + " | ".join(str(v) for v in item.values()) + " |"
                        table_rows.append(row)
                    else:
                        table_rows.append(str(item))
                result = result.replace(f'{{{key}_table}}', '\n'.join(table_rows))
            elif f'{{{key}_list}}' in result:
                # 列表格式
                list_items = [f"- {item}" for item in value]
                result = result.replace(f'{{{key}_list}}', '\n'.join(list_items))
            elif f'{{{key}}}' in result:
                # 普通数组→换行连接
                formatted = []
                for item in value:
                    if isinstance(item, dict):
                        # 字典格式化为 key: value
                        parts = [f"{k}: {v}" for k, v in item.items()]
                        formatted.append(" | ".join(parts))
                    else:
                        formatted.append(str(item))
                result = result.replace(f'{{{key}}}', '\n'.join(formatted))
        elif isinstance(value, (str, int, float)):
            # 简单类型：直接替换
            result = result.replace(f'{{{key}}}', str(value))
    
    return result


def main():
    parser = argparse.ArgumentParser(description='模板合并工具')
    parser.add_argument('--template', required=True, help='模板文件路径')
    parser.add_argument('--content', required=True, help='JSON 内容文件路径')
    parser.add_argument('--output', required=True, help='输出文件路径')
    args = parser.parse_args()
    
    # 加载
    template = load_template(args.template)
    content = json.loads(Path(args.content).read_text(encoding='utf-8'))
    
    # 合并
    result = merge_json_to_template(args.template, content)
    
    # 输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding='utf-8')
    
    print(f"[OK] 合并完成: {args.output}")


if __name__ == '__main__':
    main()
