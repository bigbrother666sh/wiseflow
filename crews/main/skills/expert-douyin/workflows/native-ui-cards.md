# 抖音原生界面卡片 Workflow

用户要做「群聊误发式」或「问答式连续讨论流」卡片并发抖音图文，或将小红书此类卡片同步到抖音时走本流程。卡片是图文 `note`，不用视频制作路线。使用 `native-ui-card` 共享技能出图；其他图文形式走 `content-production.md`。

## 1. 选题、DNA 与形态

读取 `douyin/dna/<dna-id>/<dna-id>.dna.md` 和 `.template.md`；未指定时用独立的图文 DNA（如 `dna-0-note`），不能套视频 DNA；目标 DNA 不存在先走 Style DNA workflow 建立。读取 `business_knowledge.md` 和用户素材，用 `smart-search` 核对抖音侧真实讨论。跨平台已有成品先核对内容与授权，按抖音图文 DNA 重新定标题、正文与 CTA。用户指定选题时只轻量核实，不换主题。

主题限定自媒体获客。写明常见看法与真正有依据的反常识判断，避免「大家本来就知道」的观点和绝对化口号。具体数字和案例必须可核验；不把情景演绎的聊天或评论当作真实互动。确认选题、观众及要引发的讨论后继续。

## 2. 写卡片脚本

- **群聊误发式 A**：正常群主题的 2–3 条闲聊、跨天时间戳、小贝简短误发的获客观点与红字金句、紧跟的手滑道歉、3–5 条有正反的围观回复。观点要落在画面中部，群主题与观点有自然反差。
- **问答式 B**：图 1 问题帖大标题、另一句相关搜索词、回答者头部和完整主回答；图 2 是主回答下面的反驳和缩进楼中楼；图 3 继续这条讨论，以共鸣和金句结束。不得拆成三张独立观点图。回答者身份只在图 1 头部出现一次。

界面保留「情景演绎」标识，不冒充真实群聊或抖音评论。界面数据仅在证实后写入 `verified_stats`，无法证实就留空。群友头像可从打包池选，也可以按许可另下载或 AIGC 生成，在 `avatar_sources` 写来源；不能拿真实客户肖像充当虚构群友。

## 3. 生成与审核

在 `douyin/outputs/<work-name>/` 写 `card.json`，按 [群聊示例](../../native-ui-card/examples/group.json) 或 [问答示例](../../native-ui-card/examples/qa.json) 填内容，设置 `platform: douyin` 和图文 `dna_id`。示例不作为成稿。标题 1–20 字，描述含话题 ≤1000 字，图组 1–35 张，单张 ≤50MB；本路线固定 1 或 3 张 3:4 PNG。文案只放一个平台内 CTA。

执行 `native-ui-card --input /绝对路径/card.json --output /绝对路径/douyin/outputs/<work-name>`；修订加 `--force`。它一次生成有序图片、HTML、`note.md`、`dna-meta.json` 和头像来源清单。逐张目视核对第一行、红字、消息顺序、头像加载、重叠与裁切。问答图 2/3 要让人看出是图 1 主回答下的持续争论。出图溢出就减字重渲染。向用户展示标题、正文和全部图序，确认后发布。

## 4. 抖音发布与记录

先读 `douyin-note-publish` 工具及其共用登录流程，执行 `douyin-note-publish open-page` 并检查登录状态。抖音视频和图文共用 session/发布锁，同一时间只跑一个发布任务。按顺序上传 `page-01.png`（问答式再加 `page-02.png`、`page-03.png`），上传后读取真实音乐候选，选与观点讨论氛围相符的一首；明确要原声才用 `--original-sound`。

```bash
douyin-note-publish upload --images /绝对路径/page-01.png /绝对路径/page-02.png /绝对路径/page-03.png
douyin-note-publish music-list
douyin-note-publish music-select --choice "刚返回的choice"
douyin-note-publish fill --title "已确认标题" --caption "已确认描述 #话题"
douyin-note-publish publish
douyin-note-publish get-note-link --title "已确认标题"
```

只有拿到与图文相符的 `/note/` URL 才算完成。若 `get-note-link` 显示同名标题冲突、`LINK_UNCONFIRMED` 或 exit 3，先在创作者管理页核对最新作品的完整标题和图片数并补取链接，**禁止自动重发**。登录异常或限频按工具文档处理。成功后执行：

```bash
published-track record --platform douyin --title "已发布标题" --content-type post --source-folder douyin/outputs/<work-name>/ --publish-url "确认的note URL" --account <账号alias>
```

`dna-meta.json` 已由工具生成。若同步发小红书，再按 `expert-xhs/workflows/native-ui-cards.md` 的标题、正文、探活、发布与记录流程单独处理。
