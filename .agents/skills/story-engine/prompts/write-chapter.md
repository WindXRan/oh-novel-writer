写《{新书名}》第{N}章。字数：{目标字数}字（±10%）。正文第一行"第{N}章 XXX"（不加#）。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
【源文】projects/{作者名}/{源书名}/_cache/chapters/第{N}章.txt

---

读 plot_guide → 按节拍表"新书"列逐段写。只拿骨架，具体事件全换。

**风格对标全局 style-profile（system prompt 中已注入）**——对话占比、句长分布、短句率必须一致。

写情绪用肉身反应，不写情绪词。不写源文原句。

写完直接保存。

【输出】projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt

