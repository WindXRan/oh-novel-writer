"""
测试MCP Server的功能
"""

import asyncio
import sys
from pathlib import Path

# 确保项目根目录和.mcp目录在Python路径中
project_root = Path(__file__).parent.parent
mcp_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(mcp_dir))

async def test_list_tools():
    """测试列出所有tool"""
    from server import list_tools
    
    tools = await list_tools()
    print(f"可用的Tool数量: {len(tools)}")
    print()
    
    for tool in tools:
        print(f"- {tool.name}: {tool.description[:50]}...")

async def test_story_blurb():
    """测试story_blurb tool"""
    from server import call_tool
    
    print("\n" + "=" * 50)
    print("测试 story_blurb")
    print("=" * 50)
    
    result = await call_tool("story_blurb", {
        "source_info": "源文：《替嫁新娘》，讲述女主替姐姐嫁给残疾总裁，却发现总裁是装残疾的故事。题材：现言、替嫁、甜宠。"
    })
    
    print("结果:")
    for content in result:
        print(content.text[:500] + "..." if len(content.text) > 500 else content.text)

async def test_story_review():
    """测试story_review tool"""
    from server import call_tool
    
    print("\n" + "=" * 50)
    print("测试 story_review")
    print("=" * 50)
    
    result = await call_tool("story_review", {
        "content": "第一章 替嫁\n\n沈清歌睁开眼的时候，发现自己躺在一张陌生的床上。\n\n她记得自己明明在加班，怎么突然到了这里？\n\n\"小姐，您醒了？\"一个穿着旗袍的中年女人走进来，\"婚礼马上就要开始了，您准备一下。\"\n\n婚礼？什么婚礼？\n\n沈清歌一脸懵逼。",
        "content_type": "正文",
        "review_style": "通用"
    })
    
    print("结果:")
    for content in result:
        print(content.text[:500] + "..." if len(content.text) > 500 else content.text)

async def main():
    """主测试函数"""
    print("=" * 50)
    print("MCP Server 功能测试")
    print("=" * 50)
    print()
    
    # 测试列出tool
    await test_list_tools()
    
    # 测试story_blurb（需要API Key）
    import os
    if os.environ.get("API_KEY"):
        await test_story_blurb()
        await test_story_review()
    else:
        print("\n跳过API调用测试（未设置API_KEY）")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试已停止")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()