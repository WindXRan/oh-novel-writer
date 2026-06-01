# Plan：网文作者蒸馏 Skill

> **Skill 名称**：`novel-distill`（暂定）
> **目标**：从同一作者的多本小说 txt 中提取写作风格，输出 story-style SKILL.md
> **状态**：规划中

---

## 一、方法论来源

| 仓库 | 核心方法 | 借鉴点 |
|------|---------|--------|
| **cangjie-skill** | RIA-TV++ 流水线 | 三重验证、并行提取器、结构化输出 |
| **nuwa-skill** | 6路并行采集+三重验证 | 心智模型提取、表达DNA分析 |
| **oh-story-claudecode** | 拆文+写作流程 | 章节解析、节奏分析、钩子提取 |
| **webnovel-writer** | RAG+追读力系统 | 章节统计、情绪弧线、钩子/爽点量化 |
| **AI-Writer** | RWKV模型训练 | 风格学习的思路（不直接用，参考） |

---

## 二、Skill 架构

```
.claude/skills/novel-distill/
├── SKILL.md                    # 主入口
├── methodology/
│   ├── extraction-framework.md # 提取方法论
│   ├── triple-verification.md  # 三重验证规则
│   └── output-templates.md     # 输出模板
├── extractors/
│   ├── chapter-parser.md       # 章节解析器
│   ├── style-extractor.md      # 风格提取器
│   ├── hook-extractor.md       # 钩子提取器
│   └── rhythm-extractor.md     # 节奏提取器
├── scripts/
│   ├── parse_chapters.py       # 章节解析脚本
│   ├── corpus_stats.py         # 语料统计脚本
│   └── validate_output.py      # 输出验证脚本
└── templates/
    ├── SKILL_template.md       # story-style SKILL模板
    └── meta_template.json      # meta.json模板
```

---

## 三、输入/输出规范

### 输入

```
novel-distill
├── 作者名：{name}
├── 原文路径：{path}/*.txt（至少1本，推荐3-6本）
└── 输出目录：skills/story-style/{name}/
```

**要求**：
- txt 格式，UTF-8 编码
- 每章以 `第X章` 开头
- 至少1本完整小说（推荐3本以上提取稳定风格）

### 输出

```
skills/story-style/{name}/
├── SKILL.md                    # 风格定义（story-rewrite读取）
├── meta.json                   # 量化数据（chapter_word_count等）
├── references/
│   ├── corpus-stats.md         # 语料统计详情
│   ├── hook-patterns.md        # 钩子模式库
│   ├── rhythm-patterns.md      # 节奏模式库
│   └── style-samples.md        # 风格样本
└── sources/                    # 原文备份
    └── {book_name}.txt
```

---

## 四、流水线设计（6阶段）

### Phase 1：解析与统计（Quantitative）

**目标**：从原文提取量化数据

**操作**：
1. 章节解析：按 `第X章` 分割，统计每章字数
2. 对话统计：识别对话（引号内容），计算对话占比
3. 句长分析：统计句子长度分布
4. 段落分析：统计段落长度分布
5. 禁用词扫描：统计高频词（说道、不禁、微微等）

**输出**：`corpus-stats.md` + `meta.json` 基础字段

**工具**：`scripts/corpus_stats.py`

### Phase 2：模式提取（Qualitative）

**目标**：从原文提取写作模式

**4个并行提取器**（借鉴cangjie-skill的并行提取）：

| 提取器 | 输入 | 输出 | 方法 |
|--------|------|------|------|
| **chapter-parser** | 前3章+中间3章+最后3章 | 开篇模式、结局模式 | 分析首尾100字 |
| **style-extractor** | 全文 | 句式、词汇、语气 | 统计+AI分析 |
| **hook-extractor** | 每章首尾 | 钩子类型库 | 分类+频率统计 |
| **rhythm-extractor** | 全文 | 节奏模式、情绪弧线 | 爽点分布+情绪变化 |

**输出**：4个提取器各自的报告

### Phase 3：三重验证（Triple Verification）

**借鉴**：cangjie-skill的RIA-TV++三重验证

**验证规则**：

| 验证 | 标准 | 不通过处理 |
|------|------|-----------|
| **跨书验证** | 同一模式在≥2本书中出现 | 标记为"可能偶然"，降低权重 |
| **频率验证** | 出现频率≥5%（非偶发） | 标记为"低频特征"，不作为核心风格 |
| **独特性验证** | 不是所有网文都有的通用特征 | 标记为"通用特征"，不写入风格文件 |

**通过率预期**：60-80%（过滤掉通用特征和偶发特征）

### Phase 4：风格合成（Synthesis）

**目标**：将验证通过的模式合成为 SKILL.md

**借鉴**：
- nuwa-skill的表达DNA提取
- oh-story-claudecode的章纲模板
- webnovel-writer的追读力指标

**SKILL.md 结构**：

```markdown
# {作者名} · 写作风格

## 表达DNA
- 句式偏好：[统计结果]
- 词汇特征：[高频词+禁忌词]
- 对话风格：[对话占比+标签习惯]
- 叙事视角：[第一/第三人称占比]

## 章纲模板
- 开篇模式：[前3章共性]
- 章首钩子：[高频钩子类型+示例]
- 章尾钩子：[高频钩子类型+示例]
- 爽点密度：[每X章一个爽点]
- 情绪弧线：[各卷基调]

## 写作原则
- [从原文提炼的3-5条核心原则]

## 质量检查清单
- [基于原文特征的质量标准]
```

### Phase 5：验证输出（Validation）

**目标**：验证输出的 SKILL.md 能被 story-rewrite 正确读取

**检查项**：
1. SKILL.md 包含必要 section（表达DNA、章纲模板、质量检查）
2. meta.json 字段完整（chapter_word_count、dialogue_ratio等）
3. 文件路径正确（story-rewrite能找到）

**工具**：`scripts/validate_output.py`

### Phase 6：注册到 story-style

**操作**：
1. 更新 `skills/story-style/SKILL.md` 的风格列表
2. 确认 `--style={name}` 能正确路由

---

## 五、关键技术点

### 5.1 章节解析

```python
# 伪代码
def parse_chapters(txt_path):
    content = read_file(txt_path)
    chapters = split_by_pattern(content, r'第[一二三四五六七八九十百千\d]+章')
    return [{
        'number': i,
        'title': extract_title(ch),
        'content': ch,
        'word_count': count_chars(ch),
        'dialogue_ratio': calc_dialogue_ratio(ch),
        'sentence_lengths': calc_sentence_lengths(ch)
    } for i, ch in enumerate(chapters)]
```

### 5.2 对话识别

```python
def calc_dialogue_ratio(text):
    # 识别中文引号内容
    dialogues = re.findall(r'[""][^""]*[""]', text)
    dialogue_chars = sum(len(d) for d in dialogues)
    total_chars = len(re.sub(r'\s', '', text))
    return dialogue_chars / total_chars if total_chars > 0 else 0
```

### 5.3 钩子分类

**章首钩子类型**（参考oh-story-claudecode）：
- 悬念型
- 冲突型
- 反转型
- 对话型
- 动作型
- 内心独白型
- 感官型
- 时间跳跃型

**章尾钩子类型**：
- 悬念型
- 反转钩
- 情绪高点
- 选择困境
- 信息炸弹
- 动作中断
- 对话中断
- 时间锚点

### 5.4 节奏分析

```python
def analyze_rhythm(chapters):
    # 爽点检测（基于情绪词频率）
    excitement_words = ['震惊', '不敢置信', '怎么可能', '天啊', '卧槽']
    
    # 情绪弧线（基于情绪词分类）
    positive_words = ['开心', '幸福', '甜蜜', '温暖']
    negative_words = ['痛苦', '绝望', '愤怒', '悲伤']
    
    # 输出每章的情绪分数
    return [{
        'chapter': i,
        'excitement_score': count_words(ch, excitement_words),
        'emotion_score': count_positive(ch) - count_negative(ch)
    } for i, ch in enumerate(chapters)]
```

---

## 六、与其他 Skill 的关系

```
novel-distill（本skill）
    │
    ├─ 输入：作者的多本小说 txt
    │
    ├─ 输出：skills/story-style/{name}/SKILL.md + meta.json
    │
    └─ 下游：
        ├─ story-rewrite --style={name}  → 仿写
        └─ story-style --validate={name} → 验证
```

**职责分离**：
- `novel-distill`：负责从原文提取风格（蒸馏）
- `story-style`：负责管理风格（注册+查询）
- `story-rewrite`：负责使用风格（仿写）

---

## 七、执行步骤

### Step 1：创建 Skill 目录

```powershell
mkdir .claude/skills/novel-distill
mkdir .claude/skills/novel-distill/methodology
mkdir .claude/skills/novel-distill/extractors
mkdir .claude/skills/novel-distill/scripts
mkdir .claude/skills/novel-distill/templates
```

### Step 2：编写 SKILL.md

主入口文件，定义触发方式和流程。

### Step 3：编写工具脚本

- `parse_chapters.py`：章节解析
- `corpus_stats.py`：语料统计
- `validate_output.py`：输出验证

### Step 4：编写提取器 Prompt

- `chapter-parser.md`：开篇/结局模式提取
- `style-extractor.md`：风格特征提取
- `hook-extractor.md`：钩子模式提取
- `rhythm-extractor.md`：节奏模式提取

### Step 5：编写输出模板

- `SKILL_template.md`：story-style SKILL模板
- `meta_template.json`：meta.json模板

### Step 6：测试验证

用现有的闻栖小说测试，验证输出是否与现有的 `story-style/wenqi/` 一致。

---

## 八、与现有流程的集成

```
用户：/novel-distill --author=闻栖 --path=./authors/闻栖/

Phase 1：解析 authors/闻栖/*.txt → 统计数据
Phase 2：提取模式 → 4个提取器并行
Phase 3：三重验证 → 过滤通用/偶发特征
Phase 4：合成 → 生成 SKILL.md + meta.json
Phase 5：验证 → 确认输出正确
Phase 6：注册 → 更新 story-style 路由表

结果：
- skills/story-style/闻栖/SKILL.md ✅
- skills/story-style/闻栖/meta.json ✅
- /story-rewrite --style=闻栖 可用 ✅
```

---

## 九、预期效果

| 指标 | 手动创建 | novel-distill |
|------|---------|---------------|
| 耗时 | 2-4小时 | 10-15分钟 |
| 数据完整性 | 取决于人工 | 自动化全覆盖 |
| 可验证性 | 无 | 三重验证 |
| 可复现性 | 低 | 高 |
| 与story-rewrite兼容 | 需手动适配 | 自动兼容 |

---

## 十、风险与缓解

| 风险 | 缓解 |
|------|------|
| 章节分割不准 | 支持多种分隔符（第X章、数字章号等） |
| 对话识别错误 | 多种引号格式支持（""、「」、『』） |
| 统计偏差 | 要求至少3本小说取平均 |
| 输出不符合story-style格式 | 使用模板+验证脚本 |
| 通用特征混入 | 三重验证过滤 |

---

*文档版本：V1.0*
*状态：规划中*
*下一步：创建SKILL.md和工具脚本*
