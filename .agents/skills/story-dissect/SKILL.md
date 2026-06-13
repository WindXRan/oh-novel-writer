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

### 0. 前置条件
确保源文已拆章到 `_cache/chapters/`（由 story-import 完成）。

### 1. 决定分析范围

```bash
# 使用 story-style 的风格指纹（定量锚点，增强分析质量）
python .agents/skills/story-engine/tools/calc_style_profile.py projects/{作者名}/{源书名}/_cache/chapters/第N章.txt -o projects/{作者名}/{源书名}/_cache/analysis/style_profile_N.json
```

### 2. 并行分析（5 agents 并行）

启动 5 个 agent，每个分析 1 个维度。每个 agent：
1. 读 chapters/ 下全部章节（或按采样策略读关键章节）
2. 读已有 style_profile（如有）
3. 按自身维度输出报告

全本分析 token 开销大，默认采样策略：
- ≤30章 → 全部读取
- 31-100章 → 隔章采样
- >100章 → 每3章取1章 + 首尾必取

### 3. 输出文件

```
projects/{作者名}/{源书名}/
└── _cache/source_analysis/
    ├── architecture.json      # 情节架构
    ├── conflict.json          # 冲突图谱
    ├── character_model.json   # 角色行为模型
    ├── technique.json         # 写法特征
    ├── evaluation.json        # 源文评鉴
    └── summary.md             # 汇总摘要（自动合并5维度）
```

### 4. 消费方

Phase 1（open-book）读取 `_cache/source_analysis/` 下文件：
- `evaluation.json` → 确定赛道对标策略和短板改进方向
- `architecture.json` → 弧线规划参考
- `character_model.json` → 角色行为模式脱胎换骨
- `conflict.json` → 冲突替换规划
- `technique.json` → 写作技法继承/替换决策

## 输出格式

### architecture.json
```json
{
  "phases": [
    {"name": "起", "start": 1, "end": 20, "emotion": "轻松/甜", "density": "high"}
  ],
  "turning_points": [
    {"chapter": 21, "type": "决裂", "intensity": "爆"}
  ],
  "emotion_curve": {"1": "甜", "2": "甜", "21": "虐"},
  "beat_patterns": ["误会式冲突", "第三者介入", "英雄救美"]
}
```

### conflict.json
```json
{
  "major_conflicts": [
    {"type": "身份冲突", "chapters": "1-30", "evolution": "秘密→半公开→爆发"}
  ],
  "conflict_density": {"1-10": "high", "11-20": "medium"},
  "replacement_suggestions": {
    "身份冲突": "可换为利益冲突",
    "信息差": "可换为道德困境"
  }
}
```

### character_model.json
```json
{
  "characters": [
    {
      "name": "源文角色A",
      "stress_response": "回避/压抑",
      "decision_pattern": "理性优先，但情感爆发时失控",
      "emotional_pattern": "外表冷静内心波动",
      "weakness": "过度负责",
      "arc": "从封闭到打开"
    }
  ],
  "interaction_patterns": [
    {"pair": "A-B", "pattern": "追逃模式", "evolution": "A追B逃→B主动"}
  ]
}
```

### technique.json
```json
{
  "hook_types": {"悬念式": 0.3, "情绪式": 0.4, "冲突式": 0.3},
  "scene_structure": "以对话为主(60%)",
  "dialogue_ratio": 0.55,
  "sensory_distribution": {"视觉": 0.5, "听觉": 0.2, "触觉": 0.2, "其他": 0.1},
  "avg_sentence_length": 18.5,
  "pov": "单一女主POV"
}
```

### evaluation.json
```json
{
  "dimensions": [
    {"name": "节奏", "score": 4, "strategy": "对齐"},
    {"name": "人设", "score": 3, "strategy": "改进"},
    {"name": "冲突", "score": 2, "strategy": "改进"},
    {"name": "爽点", "score": 5, "strategy": "对齐"},
    {"name": "文笔", "score": 3, "strategy": "改进"},
    {"name": "擦边浓度", "score": 4, "strategy": "对齐"}
  ],
  "core_success_factors": ["擦边节奏好", "爽点密集"],
  "must_fix": ["冲突类型单一", "配角工具化"]
}
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
