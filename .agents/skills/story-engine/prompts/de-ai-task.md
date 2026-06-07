从《{源书名}》第N章提取人类写作指纹，纯脚本生成，不走LLM。

【源文】novel-download-authors/{作者名}/{源书名}.txt（合并文件，定位到第N章）

【执行】
1. 从合并文件提取第N章，保存到临时文件
2. 运行：tools/verify_chapter.py --gen-guide <临时文件> -o novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/de-ai_guide_N.md
3. 删除临时文件

gen_guide 会自动写入：
- 字数/段落/句数
- 句长分布（短/中/长精确计数）
- 段落节奏（短/中/长段计数）
- 对话密度
- 句首多样性 + 样本
- 连接词密度
- TTR

写章agent参考这些数字对齐节奏，不是追数字。

【输出】novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/de-ai_guide_N.md

【回传】
✅ de-ai 第N章 | de-ai_guide_N.md | XXX字
