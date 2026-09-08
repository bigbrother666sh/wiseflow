# 视频号账号级 DNA 创建与更新 Workflow

本 Workflow 负责 DNA report、DNA 文档与 DNA template 的创建与更新。维度框架以 `wx-channel-style-profiler` 的 `references/account-dna-framework.md` 为准（账号级 DNA v1）。

## 边界

- DNA 是账号级运营框架，不是单条视频脚本或剪辑细节。
- 账号初始化与默认 `dna-0` 建立走 `account-setup.md`；对标样本先走 `account-benchmark.md`。
- DNA 如何用于内容生产走 `content-production.md`；改稿走 `editing.md`；数据复盘走 `review.md`。
- DNA 指导 main agent 出内容或视频 Brief；全片制作委托 `content-producer`。

## 入口判断

走本 Workflow：

- “建 DNA / 更新 DNA / 提炼这个账号的风格”
- “把这条视频落到某个 DNA 上”
- “用户提供单条或多条视频，帮我提炼可复用模式”

不走本 Workflow：

- 做内容 / 仿内容 → `content-production.md`
- 改脚本 / 换封面 / 压缩时长 → `editing.md`
- 看数据 / 评估 DNA → `review.md`
- 起号 / 定位 → `account-setup.md`
- 对标比较 → `account-benchmark.md`

## 目标 DNA 选择

1. 用户指定 `dna-id` 时使用该 DNA。
2. 未指定或说“默认 DNA”时使用 `dna-0`。
3. 对标样本必须进入独立 DNA，不直接写入 `dna-0`；采纳后再通过局部融合更新。
4. 目标 DNA 不存在时，先走 `account-setup.md` 或按用户明确指定的新 `dna-id` 初始化。

## 存储结构

```text
wx_channel/dna/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

原始脚本可临时放在 `wx_channel/ref/{dna-id}/transcripts/`。生成后的 report 必须进入目标 DNA 的 `reports/` 目录；覆盖同名 report 前先向用户说明。

## 样本获取

| 来源 | 处理 |
| --- | --- |
| 用户提供脚本 / 逐字稿 | 整理为 `.md` / `.txt`，保留描述、数据与账号线索 |
| 用户提供视频文件 | 先取得文字稿或确认转写；视频观测信息由用户/原视频补充 |
| 用户提供账号信息 | 记录昵称、简介、置顶、发布时间与内容形式 |
| 用户想法 / 偏好 | 不生成 report，按用户输入转译进入 DNA |

每条样本尽量收集：

- 样本类型：账号作品 / 用户提供单条
- 账号名、简介、主页承诺
- 发布时间、内容形式、素材来源与授权
- 播放、完播、点赞、评论、转发等数据线索
- 横竖屏、时长、口播/实拍/AIGC 形态、真人出镜占比

缺失字段写「未观测」。视频号无公开对标抓取路径，数据必须来自用户或后台工具，不得编造。

## 建立或重建 DNA

### Step 1 - 准备样本

1. 把脚本/逐字稿整理为 `.md`，首个一级标题写样本标签 / 视频简介摘要。
2. 确定目标 `dna-id`、`sample-id`、样本权重和 focus。
3. 整理账号观测与视频观测信息，供 Agent 补进 report。

### Step 2 - 生成单条 report

```bash
wx-channel-style-profiler report \
  --input path/to/script.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://channels.weixin.qq.com/..." \
  --output-dir wx_channel/dna/{dna-id}/reports
```

生成 scaffold 后必须：

1. 补齐「视频信息」与「样本与账号观测」。
2. 回读脚本原文，补齐 14 维的单条结论、证据和可复用信号。
3. 单条样本不得推导账号比例、发布节奏、社交分享闭环或高数据共性。
4. 视觉语言必须有图片/关键帧证据；口播文案 DNA 样本不足时保持未启用。

### Step 3 - 聚合 DNA

```bash
wx-channel-style-profiler build --dna-id {dna-id}
```

Agent 必须读取全部 report，按权重/focus 聚合：

- 高频共性、高权重偏好、局部借鉴、孤例、例外分开写。
- 标注样本覆盖度；单条/少量样本不得称为稳定账号 DNA。
- 高数据内容要回读创意与内容形式，不能只归因播放量。
- 为每个维度写聚合结论、报告依据和可执行规则。
- 确保 DNA 文档能推导 template。

## 更新已有 DNA

### 新增样本

生成新 report 后运行：

```bash
wx-channel-style-profiler update \
  --input wx_channel/dna/{dna-id}/reports/{new-sample}.report.md \
  --dna wx_channel/dna/{dna-id}/{dna-id}.dna.md \
  --template wx_channel/dna/{dna-id}/{dna-id}.template.md
```

再由 Agent 重新审视聚合结论并同步修订 template。

### 用户偏好

用户偏好不直接入库。通过 `--user-input` 传入后，Agent 映射到具体维度，并把原话转译为账号级规则与 Brief 规则。

### 局部借鉴

对标 DNA 的局部规则必须先说明来源、适用条件和影响维度，再融合进目标 DNA；不得整包照搬。

### 表现反馈

复盘产生的建议先列证据与影响维度，经用户确认后写入 DNA；不得把一次数据波动直接升格为账号规则。

## DNA 使用接口

- **内容生产**：读取 DNA 文档与 template，确定定位、选题、简介包装、内容形式、发布节奏和高数据创意。
- **视频全案**：main agent 产出 Brief；Brief 写明 Pipeline、素材授权、验收标准、交付边界。未指定 Pipeline 时 CP 自由发挥，指定时必须采用。
- **口播类视频**：若口播文案 DNA 已启用，main agent 写口播文案并随 Brief 交付；CP 不重写策略文案。
- **图文/长文**：main agent 直接生产。

## 对标接口

对标样本进入独立 `dna-id`；比较时输出定位、选题、简介包装、内容形式、发布节奏、高数据创意、社交分享闭环与制作管线的差异。用户明确采纳后才融合进 `dna-0`。

## 编排原则

- 一个生产任务只使用一个 DNA；需要融合时先更新 DNA。
- 样本、用户输入、数据反馈必须可追溯。
- 账号级结论必须有覆盖度；不足就写未观测。
- Template 只写 main agent 可执行的输入/Brief 规则，不写成片制作细节。
