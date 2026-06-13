---
name: story-dissect
description: |
  拆书：全本源文深度分析。提取情节架构、冲突模式、角色行为模型、写法特征、源文评鉴。
  输出标准化分析报告，供开书（Phase 1）消费。拆书只分析不创作。
  触发条件：用户说「拆书」「拆解源文」「分析源文结构」「跑拆书」。
  应优先于开书前执行。
argument-hint: <config.json>
allowed-tools: Bash(python *) Bash(ls *) Bash(mkdir *)
shell: powershell
---

# story-dissect

> Phase 0.75 拆书。只拆解，不创作。输出给开书阶段使用。

## 与 story-style 的区别

| | story-style | story-dissect |
|---|---|---|
| 粒度 | 逐章，每章独立分析 | 全书整体分析，提炼跨章模式 |
| 模式 | plot/style/hook/character（4插件） | 架构/冲突/角色模型/写法/评鉴（5维度） |
| 输出 | `analysis/{mode}_N.md`（每章一个） | `source_analysis/`（全书级报告） |
| 消费方 | plot_guide 生成（Phase 2） | 开书设定生成（Phase 1） |
| 运行时机 | Phase 1.5（guides 前） | Phase 0.75（开书前） |

## 分析维度（5维度并行）

每个维度由独立 agent 分析，并行执行：

### 1. 情节架构（architecture）
- 全书弧线阶段划分（起承转合/情绪曲线）
- 主要转折点与高潮点
- 情节密度分布（哪几章信息量大，哪几章是过渡）
- 源文情绪曲线：章节号→情绪标签 mapping
- 节拍复用模式（源文常用的节拍类型）

### 2. 冲突图谱（conflict）
- 主要冲突类型及演变路径（身份/利益/信息差/道德困境）
- 冲突密度分布
- 冲突升级模式（从 A→B→C 的链条）
- 冲突与情绪的对应关系

### 3. 角色行为模型（character-model）
- 每个核心角色的行为模式卡片：
  - 应激反应模式（危机时怎么做）
  - 决策模式（权衡什么、怎么选）
  - 情感模式（表达/压抑/逃避）
  - 弱点与保护机制
  - 成长弧线（起点→终点）
- 角色互动模式（A与B的典型互动模式）

### 4. 写法特征（technique）
- 开篇钩子模式（每章前200字的钩子类型）
- 场景结构偏好（以对话驱动/以叙事驱动/混合）
- 对话比例（对话/描写/心理占比）
- 感官运用（视觉/听觉/触觉/味觉/嗅觉的占比）
- 节奏控制（短句 vs 长句、段落长度）
- 视角运用（单一POV/多POV、切换频率）

### 5. 源文评鉴（evaluation）
- 每个维度的对标评分（1-5）
- 赛道特征提取（必须继承的点）
- 短板识别（必须改进的点）
- 模仿价值判断（哪些模式值得保留、哪些需要替换）

## 流程

**核心前提：拆书必须覆盖全书，不能只看开头。** 采样采用"情绪曲线 + 开局保障"双保险。

### 0. 前置条件
确保源文已拆章到 `_cache/chapters/` + 已有 `_toc.txt`（由 story-import 完成）。

### 1. 曲线分析 — 情绪驱动选章

读 `_toc.txt`，用 flash 分析全文情绪曲线，让 LLM 根据章节标题选出关键章节。这是最重要的一步——LLM 能识别"决裂""真相""高潮""反转"等情绪转折点，机械等距做不到。

```bash
# 复用 open_book.py 的 _detect_curve 方法
python -c "
import sys; sys.path.insert(0, '.agents/skills/story-engine/tools')
from phases.open_book import _detect_curve
# ...
"
```

选章结果合并以下规则去重：

| 来源 | 数量 | 说明 |
|------|------|------|
| LLM曲线分析 | 10-15章 | 基于情绪转折选的关键章，覆盖各弧线阶段 |
| 前15章保障 | 第1-15章 | 保证开篇分析密度（基调/角色/钩子/留存） |
| 后5章保障 | 最后5章 | 保证收尾完成度评估 |

### 2. 构建分析素材

合并所有选定章节到 `_samples.txt`，每章标注身份（开局/LLM选中/收尾）：

同时保存关键章节列表供 pipeline 复用：

```
_cache/source_analysis/_samples.txt       # 全本章节样本拼接
_cache/source_analysis/_key_chapters.json  # 关键章节号列表 [1, 15, 23, ...]
```

`_key_chapters.json` 格式：
```json
[1, 15, 23, 31, 42, 58, 66, 81, 89, 99, 114, 125, 132, 143, 153]
```

### 3. 输出文件

```
projects/{作者名}/{源书名}/
└── _cache/source_analysis/
    ├── _samples.txt            # 关键章节拼接（供 agent / API 消费）
    ├── _key_chapters.json      # 关键章节号列表 [1, 15, 23, ...]
    ├── _opening_summary.md     # 开局分析摘要（前15章，供写章阶段注入）
    ├── architecture.md         # 情节架构
    ├── conflict.md             # 冲突图谱
    ├── character_model.md      # 角色行为模型
    ├── technique.md            # 写法特征
    └── evaluation.md           # 源文评鉴
```

### 4. 消费方

Phase 1（open-book）读取 `_cache/source_analysis/` 下文件：
- `evaluation.md` → 确定赛道对标策略和短板改进方向
- `architecture.md` → 弧线规划参考
- `character_model.md` → 角色行为模式脱胎换骨
- `conflict.md` → 冲突替换规划
- `technique.md` → 写作技法继承/替换决策

## 输出格式

所有输出用 markdown，不用 JSON。结构化但保留可读性。

### architecture.md
```markdown
# 情节架构

## 弧线阶段
| 阶段 | 章节范围 | 情绪基调 | 情节密度 |
|------|---------|---------|---------|
| 起 | 1-20 | 轻松/甜 | 高 |

## 关键转折点
- 第21章：决裂（爆）
- 第45章：反转（中）

## 情绪曲线
第1章：甜 → 第2章：甜 → … → 第21章：虐

## 节拍模式
源文常用节拍：误会式冲突、第三者介入、英雄救美
```

### conflict.md
```markdown
# 冲突图谱

## 主线冲突
| 冲突类型 | 覆盖章节 | 演变路径 |
|---------|---------|---------|
| 身份冲突 | 1-30 | 秘密→半公开→爆发 |

## 冲突密度
| 章节范围 | 密度 |
|---------|------|
| 1-10 | 高 |
| 11-20 | 中 |

## 冲突替换建议
- 身份冲突 → 可换为利益冲突（同强度）
- 信息差 → 可换为道德困境（更高级）
```

### character_model.md
```markdown
# 角色行为模型

## 源文角色A
| 维度 | 描述 |
|------|------|
| 应激反应 | 回避/压抑 |
| 决策模式 | 理性优先，但情感爆发时失控 |
| 情感模式 | 外表冷静内心波动 |
| 弱点 | 过度负责 |
| 成长弧线 | 从封闭到打开 |

## 角色互动模式
| 角色对 | 模式 | 演变 |
|-------|------|------|
| A-B | 追逃模式 | A追B逃→B主动 |
```

### technique.md
```markdown
# 写法特征

## 钩子模式
| 类型 | 占比 |
|------|------|
| 悬念式 | 30% |
| 情绪式 | 40% |
| 冲突式 | 30% |

## 场景结构
以对话为主（对话60%，叙事30%，描写10%）

## 感官运用
视觉50%、听觉20%、触觉20%、其他10%

## 节奏
- 平均句长：18.5字
- 段落偏好：短段为主

## 视角
单一女主POV
```

### evaluation.md
```markdown
# 源文评鉴

## 维度评分
| 维度 | 评分 | 策略 | 说明 |
|------|------|------|------|
| 节奏 | 4/5 | 对齐 | 节奏好，保持 |
| 人设 | 3/5 | 改进 | 配角工具化，需改善 |
| 冲突 | 2/5 | 改进 | 类型单一，需丰富 |
| 爽点 | 5/5 | 对齐 | 核心卖点，必须保留 |
| 文笔 | 3/5 | 改进 | 描写偏弱 |
| 擦边浓度 | 4/5 | 对齐 | 赛道特征 |

## 核心成功因子
1. 擦边节奏好
2. 爽点密集

## 必须改进
1. 冲突类型单一
2. 配角工具化
```

## Pipeline 集成

拆书作为独立 phase 加入 pipeline：

```bash
python tools/pipeline.py --config configs/xxx.json --phase dissect
python tools/pipeline.py --config configs/xxx.json --phase open-book
# 或
python tools/pipeline.py --config configs/xxx.json --phase all
```

在 config 中 `PHASES` 注册拆书 phase（详见 phase_meta.py）：
- name: `dissect`
- depends_on: `["prep"]`
- scope: global
- parallel: false
