# 小红书原生界面卡片 Workflow

用户要做「群聊误发式」或「问答式连续讨论流」卡片，或指定用这些卡片发小红书时走本流程。它是图文笔记制作与发布的完整路线，使用 `native-ui-card` 共享技能出图；其他图文形式走 `content-production.md`。

## 1. 锁定选题与图文 DNA

读取 `xhs/dna/<dna-id>/<dna-id>.dna.md` 与 `.template.md`；未指定时用 `dna-0`，目标 DNA 不存在先走 Style DNA workflow 建立。读取 `business_knowledge.md` 和用户素材。选题限定自媒体获客，先用 `smart-search` 与 `xhs-content-ops` 查用户真实搜索问题和争议，再从 `xhs/ref/` 或已有研究提炼一条有证据的反常识判断。主问题用用户可能搜索的自然句；问答卡搜索框写另一句相关搜索词。用户已给题目则只轻量核实，不换题。

先写清「常见预期 → 新判断 → 支撑事实/条件 → 读者得到的行动」，再判断是否真的有认知差异。不得把「大家已经知道」的话包装成反常识；不得写「别涨粉」一类过度绝对化结论。案例数据、客户数、业绩和引用要有来源；无来源就改为明确的假设或不使用。确认选题、受众和搜索意图后继续。

## 2. 选形态、编讨论流

- **群聊误发式 A，单图**：选与获客观点有反差的正常群主题；2–3 条群内日常铺垫 → 跨天时间戳 → 小贝误发一条短观点，红字突出关键结论 → 紧接自然的手滑道歉 → 3–5 条质疑、共鸣、追问，把观点推到画面中部。群友语言要像不同的人，不能都是替小贝捧哏。
- **问答式 B，三图**：图 1 是显眼的问题帖 + 仅出现一次的回答者头部 + 完整主回答，回答有具体情境、转折和条件；图 2 是这条回答下的反驳、回应与缩进楼中楼；图 3 沿同一讨论继续共鸣，再用高亮金句收束。图 2/3 不重新开题，不做三个互不相干的观点切片。

这些界面是**情景演绎**。保留成图中的演绎标识，不冒充真实聊天、评论或点赞数。要显示平台数据时，只在 `verified_stats` 填已核验的数据；否则留空。

为群友选用打包头像池，也可按许可额外下载或 AIGC 生成，记录到 `avatar_sources`。用户或真实客户照片须先取得适用授权。头像用 `native-ui-card` 的 320×320 规范化输出，不手工拼本机模板路径。

## 3. 定稿并渲染

在 `xhs/outputs/<work-name>/` 建作品目录。按 [native-ui-card 群聊示例](../../native-ui-card/examples/group.json) 或 [问答示例](../../native-ui-card/examples/qa.json) 写 `card.json`，填 `platform: xhs`、图文 `dna_id`、标题（≤20 字）、正文（含话题后 ≤1000 字）、话题（≤10 个）及全部页文案。示例文本仅说明字段，不可直接发布。标题应兼顾反差与关键词；正文用金句/故事摘要 + 一个评论讨论钩子，不放联系方式或站外导流。

运行 `native-ui-card --input /绝对路径/card.json --output /绝对路径/xhs/outputs/<work-name>`；修订加 `--force`。工具固定渲染 2160×2880 PNG，并检查头像和版面溢出。逐张打开图片复核：群聊核心消息的位置、红字、第一行、头像、是否遮挡；问答图 1 的问题和主回答是否完整、身份是否重复，图 2/3 是否连续、楼中楼是否看得清。过长就精简文案并重渲染，不靠裁掉底部解决。向用户展示标题、正文、全部图序，确认后发布。

## 4. 小红书发布与记录

按 `xhs-publish` 工具文档先 `xhs-publish check`；需重登时按其消费者域与创作者 SSO 两步流程。把 `note.md` 的实际文字传给 `--body`，把图片按顺序传给 `--images`：

```bash
xhs-publish --mode image --title "已确认标题" --body "已确认正文 #话题" --images /绝对路径/page-01.png /绝对路径/page-02.png /绝对路径/page-03.png
```

群聊单图只传 `page-01.png`。仅 `ok: true` 且返回笔记 URL 才记为成功；登录、风控、限频按 `xhs-publish` 和 expert-xhs 规则处理，不盲目重发。成功后执行：

```bash
published-track record --platform xhs --title "已发布标题" --content-type post --source-folder xhs/outputs/<work-name>/ --publish-url "返回的URL" --account <账号alias>
```

`dna-meta.json` 已由工具生成。双平台分发时抖音走 `expert-douyin/workflows/native-ui-cards.md`，按抖音自己的标题、文案、发布锁与记录执行。
