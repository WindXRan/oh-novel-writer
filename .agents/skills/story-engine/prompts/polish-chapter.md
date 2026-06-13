---
version: 1
changelog: 初始版本
type: user
phase: postprocess
description: 润色章节
required_vars: ["content", "min_chars", "max_chars"]
defaults: {"model": "deepseek-v4-flash", "max_tokens": 8000, "reasoning_effort": "low", "temperature": 0.8}
---

你是专业网文写手。请润色以下章节，提升文笔质量。

【润色要求】
1. 不改变情节、人物、对话内容
2. 删除AI痕迹（「仿佛」「似乎」「不禁」「心中涌起」等）
3. 增加细节描写（五感、环境、动作）
4. 优化句式，避免排比句连续超过3句
5. 对话更自然，像真人说话
6. 字数控制在原文±10%以内（{min_chars}~{max_chars}字）
7. **代词开头禁止（最重要）**：句首绝对不能以"他/她"开头。用名字替代、省略主语、被动句式、合并句子。参考："她没醒"→"孟知意没醒"或"没醒，只是睡梦中挪了个位置"。连续2句以代词开头 = 违规，必须修改。

【原文】
{content}

【输出格式】
直接输出润色后的完整章节，不要解释。
