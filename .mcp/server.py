"""
MCP Server for Novel Writing Skills
把现有的skill包装成MCP tool，供DeepSeek V4调用
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 项目根目录（.mcp的父目录）
PROJECT_ROOT = Path(__file__).parent.parent
SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"

# 创建MCP Server
server = Server("novel-writing-tools")

# ============================================================
# Tool定义
# ============================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用的tool"""
    return [
        Tool(
            name="story_blurb",
            description="生成网文书名和简介。根据源文设定，生成网文化、口语化、有钩子的简介和书名。",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_info": {
                        "type": "string",
                        "description": "源文信息（书名、简介、核心设定、男女主等）"
                    },
                    "new_concept": {
                        "type": "string",
                        "description": "新书设定（可选，如有concept.md内容）"
                    }
                },
                "required": ["source_info"]
            }
        ),
        Tool(
            name="story_review",
            description="网文编辑审稿。根据专业模板审稿小说内容，支持通用版、女频版、毒舌版。",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "小说内容（正文或大纲）"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["正文", "大纲", "开篇"],
                        "description": "内容类型",
                        "default": "正文"
                    },
                    "review_style": {
                        "type": "string",
                        "enum": ["通用", "女频", "毒舌", "编辑"],
                        "description": "审稿风格",
                        "default": "通用"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="story_engine_open_book",
            description="开书阶段：分析源文，生成新书设定（concept.md）。包括设定、角色名、角色行为模式、全局节奏图、弧线。",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "配置文件路径（JSON格式）"
                    }
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="story_engine_guides",
            description="生成章节指南：为指定章节生成plot_guide和style_guide。",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "配置文件路径"
                    },
                    "start_chapter": {
                        "type": "integer",
                        "description": "起始章节号",
                        "default": 1
                    },
                    "end_chapter": {
                        "type": "integer",
                        "description": "结束章节号",
                        "default": 1
                    }
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="story_engine_write",
            description="写章阶段：根据guide生成正文章节。",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "配置文件路径"
                    },
                    "start_chapter": {
                        "type": "integer",
                        "description": "起始章节号",
                        "default": 1
                    },
                    "end_chapter": {
                        "type": "integer",
                        "description": "结束章节号",
                        "default": 1
                    },
                    "workers": {
                        "type": "integer",
                        "description": "并行数",
                        "default": 5
                    }
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="story_engine_validate",
            description="质量验证：检查字数、比喻、AI路标词、台词抄袭等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "配置文件路径"
                    },
                    "start_chapter": {
                        "type": "integer",
                        "description": "起始章节号",
                        "default": 1
                    },
                    "end_chapter": {
                        "type": "integer",
                        "description": "结束章节号",
                        "default": 1
                    }
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="story_engine_full_pipeline",
            description="完整仿写流水线：开书→指南→写章→验证→修复→对比→导出。",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "配置文件路径"
                    },
                    "start_chapter": {
                        "type": "integer",
                        "description": "起始章节号",
                        "default": 1
                    },
                    "end_chapter": {
                        "type": "integer",
                        "description": "结束章节号",
                        "default": 10
                    },
                    "workers": {
                        "type": "integer",
                        "description": "并行数",
                        "default": 10
                    }
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="story_compare",
            description="生成仿写书与源文的逐章对比文件。",
            inputSchema={
                "type": "object",
                "properties": {
                    "rewrites_dir": {
                        "type": "string",
                        "description": "仿写书目录路径"
                    },
                    "start_chapter": {
                        "type": "integer",
                        "description": "起始章节号",
                        "default": 1
                    },
                    "end_chapter": {
                        "type": "integer",
                        "description": "结束章节号",
                        "default": 3
                    }
                },
                "required": ["rewrites_dir"]
            }
        ),
        Tool(
            name="story_scan",
            description="番茄小说排行榜分析。自动采集榜单数据，生成趋势分析和创作建议。",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["scrape", "build", "serve", "all", "status"],
                        "description": "操作类型",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="story_optimize",
            description="根据审稿反馈提取通用优化规则，沉淀到prompt里。",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback": {
                        "type": "string",
                        "description": "审稿反馈内容"
                    },
                    "target_prompt": {
                        "type": "string",
                        "enum": ["plot-guide", "style-guide", "open-book"],
                        "description": "目标prompt文件"
                    }
                },
                "required": ["feedback"]
            }
        )
    ]

# ============================================================
# Tool执行
# ============================================================

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """执行指定的tool"""
    try:
        if name == "story_blurb":
            return await execute_story_blurb(arguments)
        elif name == "story_review":
            return await execute_story_review(arguments)
        elif name == "story_engine_open_book":
            return await execute_story_engine_open_book(arguments)
        elif name == "story_engine_guides":
            return await execute_story_engine_guides(arguments)
        elif name == "story_engine_write":
            return await execute_story_engine_write(arguments)
        elif name == "story_engine_validate":
            return await execute_story_engine_validate(arguments)
        elif name == "story_engine_full_pipeline":
            return await execute_story_engine_full_pipeline(arguments)
        elif name == "story_compare":
            return await execute_story_compare(arguments)
        elif name == "story_scan":
            return await execute_story_scan(arguments)
        elif name == "story_optimize":
            return await execute_story_optimize(arguments)
        else:
            return [TextContent(type="text", text=f"未知的tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"执行失败: {str(e)}")]

# ============================================================
# 具体执行函数
# ============================================================

async def execute_story_blurb(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行书名简介生成"""
    source_info = arguments.get("source_info", "")
    new_concept = arguments.get("new_concept", "")
    
    # 构建prompt
    prompt = f"""根据以下源文信息，生成网文书名和简介。

【源文信息】
{source_info}

【新书设定】
{new_concept if new_concept else "暂无，根据源文推断"}

请生成：
1. 5个候选书名（网文感强，有记忆点，不与源文撞梗）
2. 5个候选简介（悬念型、冲突型、情感型、反转型、口语型各一个）

要求：
- 书名：网文感强，参考番茄/七猫热榜
- 简介：200-300字，口语化，有钩子，结尾留悬念
- 避免AI感（不要用"悬着的心终于死了"这种）"""

    # 调用DeepSeek API
    result = await call_deepseek_api(prompt)
    return [TextContent(type="text", text=result)]

async def execute_story_review(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行审稿"""
    content = arguments.get("content", "")
    content_type = arguments.get("content_type", "正文")
    review_style = arguments.get("review_style", "通用")
    
    # 加载审稿模板
    template_path = SKILLS_DIR / "story-engine" / "prompts" / "review-template.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = "你是专业网文编辑，请审稿。"
    
    # 根据风格选择模板
    if review_style == "女频":
        style_prompt = "请按照女频言情版审稿标准分析。"
    elif review_style == "毒舌":
        style_prompt = "请不要只做鼓励式评价，像真正要决定签约与否的编辑一样审稿。结论要明确，问题要尖锐。"
    elif review_style == "编辑":
        style_prompt = "请模拟小说平台责编写审稿意见。"
    else:
        style_prompt = ""
    
    prompt = f"""{template}

{style_prompt}

【内容类型】{content_type}

【小说内容】
{content}"""

    result = await call_deepseek_api(prompt)
    return [TextContent(type="text", text=result)]

async def execute_story_engine_open_book(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行开书阶段"""
    config_path = arguments.get("config_path", "")
    
    if not Path(config_path).exists():
        return [TextContent(type="text", text=f"配置文件不存在: {config_path}")]
    
    # 调用rewrite_chapters.py的open-book阶段
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-engine" / "tools" / "rewrite_chapters.py"),
        "--config", config_path,
        "--phase", "open-book"
    ]
    
    result = await run_subprocess(cmd)
    return [TextContent(type="text", text=result)]

async def execute_story_engine_guides(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行指南生成阶段"""
    config_path = arguments.get("config_path", "")
    start = arguments.get("start_chapter", 1)
    end = arguments.get("end_chapter", 1)
    
    if not Path(config_path).exists():
        return [TextContent(type="text", text=f"配置文件不存在: {config_path}")]
    
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-engine" / "tools" / "rewrite_chapters.py"),
        "--config", config_path,
        "--phase", "guides",
        "--start", str(start),
        "--end", str(end)
    ]
    
    result = await run_subprocess(cmd)
    return [TextContent(type="text", text=result)]

async def execute_story_engine_write(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行写章阶段"""
    config_path = arguments.get("config_path", "")
    start = arguments.get("start_chapter", 1)
    end = arguments.get("end_chapter", 1)
    workers = arguments.get("workers", 5)
    
    if not Path(config_path).exists():
        return [TextContent(type="text", text=f"配置文件不存在: {config_path}")]
    
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-engine" / "tools" / "rewrite_chapters.py"),
        "--config", config_path,
        "--phase", "write",
        "--start", str(start),
        "--end", str(end),
        "--workers", str(workers)
    ]
    
    result = await run_subprocess(cmd)
    return [TextContent(type="text", text=result)]

async def execute_story_engine_validate(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行质量验证"""
    config_path = arguments.get("config_path", "")
    start = arguments.get("start_chapter", 1)
    end = arguments.get("end_chapter", 1)
    
    if not Path(config_path).exists():
        return [TextContent(type="text", text=f"配置文件不存在: {config_path}")]
    
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-engine" / "tools" / "rewrite_chapters.py"),
        "--config", config_path,
        "--phase", "validate",
        "--start", str(start),
        "--end", str(end)
    ]
    
    result = await run_subprocess(cmd)
    return [TextContent(type="text", text=result)]

async def execute_story_engine_full_pipeline(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行完整流水线"""
    config_path = arguments.get("config_path", "")
    start = arguments.get("start_chapter", 1)
    end = arguments.get("end_chapter", 10)
    workers = arguments.get("workers", 10)
    
    if not Path(config_path).exists():
        return [TextContent(type="text", text=f"配置文件不存在: {config_path}")]
    
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-engine" / "tools" / "rewrite_chapters.py"),
        "--config", config_path,
        "--phase", "all-with-fix",
        "--start", str(start),
        "--end", str(end),
        "--workers", str(workers)
    ]
    
    result = await run_subprocess(cmd, timeout=3600)  # 1小时超时
    return [TextContent(type="text", text=result)]

async def execute_story_compare(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行对比生成"""
    rewrites_dir = arguments.get("rewrites_dir", "")
    start = arguments.get("start_chapter", 1)
    end = arguments.get("end_chapter", 3)
    
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "story-compare" / "compare.py"),
        rewrites_dir,
        str(start),
        str(end)
    ]
    
    result = await run_subprocess(cmd)
    return [TextContent(type="text", text=result)]

async def execute_story_scan(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行番茄扫描"""
    action = arguments.get("action", "all")
    
    scan_dir = SKILLS_DIR / "story-scan" / "FanqieZhiShu"
    cmd = [
        sys.executable,
        str(scan_dir / "run.py"),
        action
    ]
    
    result = await run_subprocess(cmd, timeout=600)  # 10分钟超时
    return [TextContent(type="text", text=result)]

async def execute_story_optimize(arguments: Dict[str, Any]) -> List[TextContent]:
    """执行规则沉淀"""
    feedback = arguments.get("feedback", "")
    target_prompt = arguments.get("target_prompt", "plot-guide")
    
    prompt = f"""根据以下审稿反馈，提取通用优化规则，沉淀到{target_prompt}。

【审稿反馈】
{feedback}

请分析：
1. 这个问题是个例还是通用？
2. 如果通用，提取成一条可执行规则
3. 规则必须：可执行、可验证、有正反例

输出格式：
【问题分析】
【规则】
【正例】
【反例】
【沉淀位置】{target_prompt}"""

    result = await call_deepseek_api(prompt)
    return [TextContent(type="text", text=result)]

# ============================================================
# 工具函数
# ============================================================

async def call_deepseek_api(prompt: str, system_prompt: str = None) -> str:
    """调用DeepSeek API"""
    import httpx
    
    api_key = os.environ.get("API_KEY")
    if not api_key:
        return "错误：未设置API_KEY环境变量"
    
    api_url = os.environ.get("API_BASE_URL", "https://api.deepseek.com")
    if not api_url.endswith("/chat/completions"):
        api_url = api_url.rstrip("/") + "/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt or "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 8192
    }
    
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

async def run_subprocess(cmd: List[str], timeout: int = 300) -> str:
    """运行子进程"""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        output = stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\n\n[STDERR]\n" + stderr.decode("utf-8", errors="replace")
        
        return output
    except asyncio.TimeoutError:
        return f"执行超时（{timeout}秒）"
    except Exception as e:
        return f"执行失败: {str(e)}"

# ============================================================
# 启动服务器
# ============================================================

async def main():
    """启动MCP Server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())