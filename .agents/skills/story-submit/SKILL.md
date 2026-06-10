# Skill: story-submit

# story-submit · 自动投稿

将导出的小说txt自动投稿到蛙蛙写作平台。

## 触发条件

用户说：`/submit`、`投稿`、`自动投稿`、`上传到蛙蛙`

## 前置条件

1. 已登录蛙蛙写作平台（Chrome保持登录状态）
2. 已导出小说txt文件
3. 已安装playwright：`pip install playwright && playwright install chromium`

## 使用方式

```powershell
python .agents/skills/story-submit/submit.py --book <导出的txt文件路径>
```

示例：
```powershell
python .agents/skills/story-submit/submit.py --book "projects/闻栖/分手了？秦少火速领证上位/rewrites/分手了？秦少火速领证上位仿写/export/他说我配不上？转身我成了他对手.txt"
```

## 投稿流程

1. 解析txt文件，提取书名、简介、分类、标签
2. 启动浏览器，打开投稿页面：https://wawawriter.com/app/submission/create
3. 自动填写表单（书名、简介等）
4. 上传章节内容
5. 提交投稿

## 文件结构

```
.agents/skills/story-submit/
├── SKILL.md
└── submit.py
```

## 注意事项

- 首次使用需要手动登录蛙蛙平台
- 登录状态会保存在Chrome用户数据目录中
- 脚本使用playwright进行浏览器自动化
