---
version: 16
changelog: 恢复节拍强约束+简短
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "女主名", "男主名", "分析_开局", "分析_跨书参考", "质量反馈"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 4096, "reasoning_effort": "low", "temperature": 0.8}
---

写《{新书名}》第{N}章。正文第一行写"第{N}章 [章名]"，章名使用下方 plot_guide 中标注的。

**每行正文都必须对应 plot_guide 里的一个节拍。找不到所属节拍的行 → 删。**
**节拍顺序即法律。** #1→#2→#3→...，不能跳不能创不能重排。

【plot_guide】{rewrites_dir}/guides/plot_{N}.md
【设定】{rewrites_dir}/settings/characters.md
【设定】{rewrites_dir}/settings/book_info.md
【设定】{rewrites_dir}/settings/world.md
【品类参考】{rewrites_dir}/settings/source_analysis.md
{分析_开局}
{质量反馈}

---

## 方法

• 数 plot_guide 的节拍数 = N → 每拍约 {目标字数}/N 字，拍完核查字数
• 每拍写一段，按 #1→#2→...#N 写。每段只做那一拍标注的事
• 选一拍做记忆点（放慢写，给足画面/细节），选一拍做高光（情绪最强）
• 末句必须是钩子。擦边对标源文
• **总字数 ≤ {目标字数_max}，超额则删描写/缩对话/砍枝节**

## 禁止

• 源文中的任何人名、地名、编号
• 角色职业/身份偏离【设定】文件
• 创造 plot_guide 中没有的节拍
• 复制源文的剧情结构/动作链

---

## 输出

【输出】{rewrites_dir}/chapters/ch_{N}.txt
