# AI网文小说项目 — 仿写引擎

## 核心原则

**任何优化针对 workflow，不针对产出内容。** 不修单章，只修 pipeline。每次抽卡自动出稿，0 人工。

防线在流程里（规则在 prompt 文件里，不在本文档）：
- 冲突类型强制换
- 台词 0 重合
- 换皮检验：剥掉人名地名，认不出源文→合格

## 我的行为规则

1. **内容规则看 prompt 文件**，`CLAUDE.md` 只放 agent 行为规则
2. **不动 CLAUDE.md**，除非改行为规则
3. **不动 README/docs**，除非用户要求
4. **不改单章**，只修 pipeline 或 prompt
5. **ASK 再执行** — 用户说什么我做什么，不猜意图
6. **用户说"仿写"/"写小说"** → 先问哪个项目、从哪步开始

## 技术参考（指向代码，不硬编码）

- **pipeline 阶段**: `tools/pipeline.py --help` 或看 `tools/phases/` 目录
- **技能列表**: 看 system prompt 的 available_skills
- **配置格式**: 看任意 `configs/xxx.json` 示例
- **文件结构**: 实际目录看 `projects/` 下的项目
- **全量命令**: `tools/rewrite_chapters.py --help`
- **prompt 规则**: 写在 `.agents/skills/story-engine/prompts/` 各文件里

## 不变的结构

```
dissect → open-book → write → review
  分析源文   生成设定    写章    审改

write 阶段会自动补缺失的 plot_guide（JIT），不需要前置跑 guides 阶段。
```

## 双执行模式

| 模式 | 说明 |
|------|------|
| `api` | Python 脚本调 API，批量生产 |
| `agent` | opencode agent 派生子 agent 写章，不调 API |

`config.json` 的 `execution_mode` 控制，可按 phase 覆盖。
