---
name: native-ui-card
description: 把自媒体获客主题做成群聊误发式单图或问答式三图连续讨论流；供 expert-xhs 和 expert-douyin 图文 workflow 制作可发布卡片。
metadata:
  openclaw:
    emoji: 🗂️
---

# 原生界面卡片制作

由平台专家 workflow 决定选题、发布和记录；本技能只负责把已定稿内容渲染为图片与作品文件。通过 PATH 调用 `native-ui-card --input /绝对路径/card.json --output /绝对路径/作品目录`。修改同一作品时加 `--force`。不要拼脚本路径，不要直接改打包 CSS。

输入示例分别见 [群聊单图](examples/group.json) 和 [问答三图](examples/qa.json)。复制示例到作品目录，替换全部文案和事实，再运行 wrapper。JSON 的 `platform` 设为 `xhs` 或 `douyin`；`dna_id` 填该平台的图文 DNA。工具使用系统 Chrome/Chromium、仓内 headless shell 或已安装的 `camoufox-cli` 渲染，不借用平台登录会话。生成 `page-01.png`（群聊）或按顺序的 `page-01.png` 至 `page-03.png`（问答），同时生成 HTML、`note.md`、`dna-meta.json`、`card.json`、`assets-manifest.json`。图片固定 2160×2880；如文本遮挡、头像失效或版面溢出，命令直接报错，精简文案后重渲染，并逐张目视复核。

## 内容约束

- 选题只围绕自媒体获客，反差要给读者一个可验证的新判断。观点保留条件，不写无依据的绝对断言。真实案例、客户结果和业绩数字必须可核验；界面互动数只用于画面呈现，不能当作业务成效的证据。
- 群聊：`before` 是与群主题相符的日常话题，`point` 是小贝误发的获客观点，`highlight` 必须是 `point` 的原句；接着 `apology`，`after` 至少三条质疑、共鸣或追问。群主题与误发观点应有明显反差。
- 问答：图 1 的 `question` 是显眼的主问题，`search` 是另一句相关搜索词；`answer` 是完整主回答，只在头部展示一次回答者身份。`pages[0]` 和 `pages[1]` 都是这条回答下面继续发生的跟帖，按图 2、图 3 的阅读顺序写；图 2 至少有一条 `reply` 楼中楼，图 3 用共鸣和一句有记忆点的收束。
- 昵称、时间戳、群人数、回复关系和界面数字要自然且前后一致。问答图 1 可选填 `stats`，展示「关注」「回答」「浏览」数；不需要另加说明性角标。发布文案直接承接卡片观点和讨论。

## 头像

默认头像池是随技能打包的 30 张方图，引用 `avatar-01.jpg` 至 `avatar-30.jpg`；小贝头像引用 `xiaobei-avatar.jpg`。群友头像也可以用 `pexels-footage` 从有使用许可的图库另行下载，或用 `awk-img-gen` AIGC 生成；把本地绝对路径或相对输入 JSON 的路径写进 `avatar`，在 `avatar_sources` 中按该路径记录来源、授权或生成方式。脚本会检查图片、裁成 320×320 方图并复制到作品目录。不要把真实客户头像或个人照片当作虚构群友使用。

## 发布交接

读取 `note.md`，按平台规则检查标题、正文与话题；发布命令接收实际文字，不把文件路径当正文。成功拿到作品 URL 后，由对应 expert workflow 调 `published-track record`，分别存入平台作品目录。两平台分发要各自有标题、正文、`dna-meta.json` 和发布记录。
