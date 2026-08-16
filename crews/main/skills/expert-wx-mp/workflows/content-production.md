# 内容生产 Workflow

从选题到发布的完整文章生产。用户说“帮我写一篇 XX”“出几篇稿子”“写篇公众号”走这个。

## Step 0 - 前置准备

**先确定内容 DNA。**
- 有指定风格 / 指定账号 -> 走 `style-dna.md` 建好 DNA
- 有历史 DNA 可用 -> 读取 `dna/wx_mp/<dna-id>.md` 的「使用时必须执行」
- 都没有 -> 向用户确认后用 `dna/wx_mp/default-business.md`

**再看缺不缺信息：**
- 文章主题 / 方向是什么
- 目标读者是谁（不确定就按账号定位来）
- 手上有什么素材（文案、笔记、截图、参考链接）
- 要不要打分、要不要发布

缺信息一次问清，不挤牙膏。

## Step 1 - 选题（按需）

- 有明确主题 -> 跳过，直接到 Step 2
- 只有方向没有具体选题 -> 调 `wechat-topic-outline-planner` 出 3-5 个选题方向
- 需要对标参考 -> 调顶层 `wx-mp-hunter` 抓对标文章
- 给用户选，或者直接推荐最优的一个

## Step 2 - 大纲

- 调 `wechat-topic-outline-planner` 把选题转成结构化大纲
- 产出：大纲 + 开头钩子选项 + 结尾方案

## 【确认】选题 + 大纲

方向对不对、结构行不行--这是第一个必停节点。
- 确认的是方向和结构，不是每个字
- 大调回 Step 1/2，小调直接改

## Step 3 - 初稿

- 调 `wechat-draft-writer` 按 DNA instruction + 大纲写初稿
- 默认字数 1500-2500，特殊需求另说
- 统计型 DNA 运行 `wechat-style-profiler evaluate`；手写 DNA 按 `.evaluation.md` 自评
- 总分低于 80 先修订，再重新计算

## 【确认】初稿方向

第二个必停节点。
- 小修小改直接处理
- 大调（换角度/换结构/换语气）回前面重写
- OK 就往下走

## Step 4 - 标题

- 调 `wechat-title-generator` 出 8 个候选 + 打分
- 给用户 3 个选项：最推荐 / 最稳妥 / 最强传播
- 用户也可以自己改

## Step 5 - 排版主题（独立于 DNA）

**Agent 自己选，不丢给 relay 默认。**
- 根据内容类型和阅读场景，先看 `wenyan-theme/index.json` 有无可复用主题，再从内置主题里挑最合适的
- 要对标排版 / 用户指定了参考文章 -> 调 `generate-wenyan-theme` 生成自定义主题
- 生成后保存到 `wenyan-theme/<theme-id>.css`，并在 `wenyan-theme/index.json` 登记 `theme-id`
- 用户直接指定了主题 -> 用用户指定的

## Step 6 - 打分（可选）

- 用户要求打分 -> 走 `content-calibrator` blind sub-agent 7 维打分 + 盲预测
- 没提 -> 不主动加，但可以问一句“要不要跑个分”
- 阈值门以 `calibration/.cheat-state.json` 为准

## Step 7 - 存文件

`output_articles/<article-name>/` 下放好：
- `article.md`
- 封面图 + 配图
- `dna-evaluation.json`（统计型 DNA 时）
- `calibration/`（打了分的话）

## 【确认】发布前检查

第三个必停节点。检查清单在 `wx-mp-publisher` 工具说明末尾，核心是：
- 内容合规（敏感表述、夸大、版权）
- 格式正常（图片、标题长度、作者）
- 链接正确
- 发对账号

## Step 8 - 发布 + 记录

- 调 `wx-mp-publisher` 推草稿箱；自定义主题传 `theme-id`，不修改 publisher 说明书主题表
- 告诉用户去后台确认手动发布
- 发布完成后调 `published-track record.sh` 落库
