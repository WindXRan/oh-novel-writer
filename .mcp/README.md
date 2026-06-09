# Novel Writing MCP Server

把现有的网文创作skill包装成MCP tool，供DeepSeek V4通过opencode调用。

## 快速开始

### 1. 设置环境变量

```powershell
# 设置API Key
$env:API_KEY = "your-deepseek-api-key"

# 可选：设置API Base URL（默认使用DeepSeek官方）
$env:API_BASE_URL = "https://api.deepseek.com"
```

### 2. 启动MCP Server

```powershell
# 方式1：直接运行
python mcp_server.py

# 方式2：使用便捷脚本
python start_mcp_server.py
```

### 3. 配置opencode

在项目根目录创建 `.opencode/mcp.json`：

```json
{
  "mcpServers": {
    "novel-writing": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "API_KEY": "${API_KEY}",
        "API_BASE_URL": "${API_BASE_URL:-https://api.deepseek.com}"
      },
      "cwd": "C:\\Users\\Administrator\\Documents\\trae_projects\\AI网文小说项目"
    }
  }
}
```

## 可用的Tool

### 1. story_blurb - 生成书名简介

根据源文设定，生成网文化、口语化、有钩子的简介和书名。

**参数：**
- `source_info` (必填): 源文信息（书名、简介、核心设定、男女主等）
- `new_concept` (可选): 新书设定

**示例：**
```json
{
  "source_info": "源文：《替嫁新娘》，讲述女主替姐姐嫁给残疾总裁，却发现总裁是装残疾的故事",
  "new_concept": "改为穿越设定，女主穿越到书中成为替嫁新娘"
}
```

### 2. story_review - 网文编辑审稿

根据专业模板审稿小说内容，支持多种审稿风格。

**参数：**
- `content` (必填): 小说内容（正文或大纲）
- `content_type` (可选): 内容类型，可选 `正文`、`大纲`、`开篇`，默认 `正文`
- `review_style` (可选): 审稿风格，可选 `通用`、`女频`、`毒舌`、`编辑`，默认 `通用`

**示例：**
```json
{
  "content": "第一章 替嫁\n\n沈清歌睁开眼的时候...",
  "content_type": "正文",
  "review_style": "女频"
}
```

### 3. story_engine_open_book - 开书阶段

分析源文，生成新书设定（concept.md）。

**参数：**
- `config_path` (必填): 配置文件路径（JSON格式）

**配置文件示例：**
```json
{
  "book_name": "新书名",
  "author": "作者名",
  "source_book": "源书名",
  "api_key": null,
  "model": "deepseek-chat",
  "rewrites_dir": "projects/作者/源书/rewrites/新书"
}
```

### 4. story_engine_guides - 生成章节指南

为指定章节生成plot_guide和style_guide。

**参数：**
- `config_path` (必填): 配置文件路径
- `start_chapter` (可选): 起始章节号，默认 1
- `end_chapter` (可选): 结束章节号，默认 1

### 5. story_engine_write - 写章阶段

根据guide生成正文章节。

**参数：**
- `config_path` (必填): 配置文件路径
- `start_chapter` (可选): 起始章节号，默认 1
- `end_chapter` (可选): 结束章节号，默认 1
- `workers` (可选): 并行数，默认 5

### 6. story_engine_validate - 质量验证

检查字数、比喻、AI路标词、台词抄袭等。

**参数：**
- `config_path` (必填): 配置文件路径
- `start_chapter` (可选): 起始章节号，默认 1
- `end_chapter` (可选): 结束章节号，默认 1

### 7. story_engine_full_pipeline - 完整仿写流水线

一键完成：开书→指南→写章→验证→修复→对比→导出。

**参数：**
- `config_path` (必填): 配置文件路径
- `start_chapter` (可选): 起始章节号，默认 1
- `end_chapter` (可选): 结束章节号，默认 10
- `workers` (可选): 并行数，默认 10

### 8. story_compare - 生成对比文件

生成仿写书与源文的逐章对比文件。

**参数：**
- `rewrites_dir` (必填): 仿写书目录路径
- `start_chapter` (可选): 起始章节号，默认 1
- `end_chapter` (可选): 结束章节号，默认 3

### 9. story_scan - 番茄排行榜分析

自动采集榜单数据，生成趋势分析和创作建议。

**参数：**
- `action` (可选): 操作类型，可选 `scrape`、`build`、`serve`、`all`、`status`，默认 `all`

### 10. story_optimize - 规则沉淀

根据审稿反馈提取通用优化规则，沉淀到prompt里。

**参数：**
- `feedback` (必填): 审稿反馈内容
- `target_prompt` (可选): 目标prompt文件，可选 `plot-guide`、`style-guide`、`open-book`

## 使用示例

### 在opencode中使用

配置好MCP Server后，在opencode中可以直接使用：

```
用户：帮我生成一个替嫁题材的书名和简介

opencode：我来调用story_blurb tool为您生成...
```

### 在Python中调用

```python
import asyncio
from mcp.server import Client

async def main():
    async with Client("novel-writing") as client:
        # 生成书名简介
        result = await client.call_tool("story_blurb", {
            "source_info": "替嫁题材，女主替姐姐嫁给残疾总裁"
        })
        print(result)

asyncio.run(main())
```

## 故障排除

### 1. API Key未设置

```
错误：未设置API_KEY环境变量
```

**解决：** 设置环境变量 `$env:API_KEY = "your-api-key"`

### 2. MCP Server启动失败

```
错误：No module named 'mcp'
```

**解决：** 安装MCP SDK `pip install mcp`

### 3. Tool执行超时

```
执行超时（300秒）
```

**解决：** 增加超时时间，或减少并行数

## 架构说明

```
opencode (DeepSeek V4)
    │
    │ tool_call: "story_blurb"
    │ args: { source_info: "..." }
    │
    ▼
MCP Server (Python)
    │
    ├─ story_blurb        → 调用DeepSeek API生成
    ├─ story_review       → 加载模板 + DeepSeek API
    ├─ story_engine_*     → 调用rewrite_chapters.py
    ├─ story_compare      → 调用compare.py
    └─ story_scan         → 调用run.py
```

## 注意事项

1. **全部使用DeepSeek**：所有API调用都使用DeepSeek V4，不依赖Claude
2. **Windows兼容**：所有路径和命令都适配Windows环境
3. **异步执行**：所有Tool都是异步执行，支持并发
4. **错误处理**：所有Tool都有完善的错误处理和超时机制