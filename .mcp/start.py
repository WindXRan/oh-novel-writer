"""
启动MCP Server的便捷脚本
"""

import os
import sys
import asyncio
from pathlib import Path

# 确保项目根目录和.mcp目录在Python路径中
project_root = Path(__file__).parent.parent
mcp_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(mcp_dir))

# 检查环境变量
def check_env():
    """检查必要的环境变量"""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("警告：未设置API_KEY环境变量")
        print("请设置：")
        print("  PowerShell: $env:API_KEY = 'your-api-key'")
        print("  CMD: set API_KEY=your-api-key")
        print()
    
    api_base = os.environ.get("API_BASE_URL", "https://api.deepseek.com")
    print(f"API Base URL: {api_base}")
    print(f"API Key: {'已设置' if api_key else '未设置'}")
    print()

def main():
    """主函数"""
    print("=" * 50)
    print("Novel Writing MCP Server")
    print("=" * 50)
    print()
    
    check_env()
    
    print("可用的Tool：")
    print("  1. story_blurb - 生成书名简介")
    print("  2. story_review - 网文编辑审稿")
    print("  3. story_engine_open_book - 开书阶段")
    print("  4. story_engine_guides - 生成章节指南")
    print("  5. story_engine_write - 写章阶段")
    print("  6. story_engine_validate - 质量验证")
    print("  7. story_engine_full_pipeline - 完整仿写流水线")
    print("  8. story_compare - 生成对比文件")
    print("  9. story_scan - 番茄排行榜分析")
    print("  10. story_optimize - 规则沉淀")
    print()
    
    print("启动MCP Server...")
    print("按 Ctrl+C 停止")
    print()
    
    # 导入并运行MCP Server
    from server import main as mcp_main
    asyncio.run(mcp_main())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMCP Server已停止")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)