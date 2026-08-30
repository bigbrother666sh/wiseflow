# 视频号风格 DNA 创建与更新 Workflow

本 Workflow 只负责风格 DNA 三层产物的创建与更新：判断样本来源、选择目标 DNA、获取样本文字稿与封面、调用 `wx-channel-style-profiler` 生成或更新 report / DNA 文档 / template。16 维（v0）提取与聚合方法以 `wx-channel-style-profiler` 为准。

边界说明：

- 账号初始化、定位梳理与默认 `dna-0` 初始化走 `account-setup.md`（该 workflow 会调用本 workflow 的样本获取与更新机制）。
- 账号对标分析走 `account-benchmark.md`；本 workflow 只承担对标 DNA 的三层产物生成与更新，以及采纳后并入基线 DNA 的更新。
- DNA 如何被用于视频生产（含仿照创作、脚本改写）由 `content-production.md` 规定，改稿由 `editing.md` 规定；本 workflow 不描述生产过程。

DNA 描述选题、标题与描述文案、封面、脚本结构与表达策略。视频成片的制作工艺（剪辑、特效）不属于 DNA。

> **维度版本**：16 维为 v0 定稿（2026-08-27 用户确认，见 `wx-channel-style-profiler` 的 `references/video-dna-dimensions.md`）；后续维度如有升版本调整，历史 report 的维度编号以生成时版本为准。

## 入口判断

走本 Workflow：

- “建 DNA / 更新 DNA / 提炼这条视频的风格”
- “把这条视频落到某个 DNA 上”
- “提取下这个账号的视频风格 DNA”

不走本 Workflow：

- “帮我做条视频 / 照着这条仿一条 / 这个主题我们也做一条”（使用 DNA 生产）-> 走 `content-production.md`
- “改改这条的脚本 / 换个钩子” -> 走 `editing.md`
- “看数据 / 复盘 / 诊断这条” -> 走 `review.md`
- “起号 / 梳理账号定位” -> 先走 `account-setup.md`
- “分析对标账号 / 对比风格差异” -> 走 `account-benchmark.md`

## 目标 DNA 选择

1. 用户明确指定 `dna-id` 时，使用该 DNA。
2. 用户明确说“落到默认 DNA”或未指定目标时，使用 `dna-0`。
3. 用户意图是账号对标、模式对比时，走 `account-benchmark.md`，对标样本必须进入独立 `dna-id`，不得直接写入 `dna-0`。
4. 找不到目标 DNA 文档时，先走 `account-setup.md` 建立 `dna-0`，或按用户明确指定的新 `dna-id` 初始化。

默认规则：

- 除 `account-benchmark.md` 分流的对标样本外，未特别分流的新参考视频样本累积到 `dna-0`。
- `dna-0` 不代表某个参考账号，而是当前工作区的默认内容生产规则集。
- 用户可以随时把样本、偏好或局部借鉴明确落到任意已有 DNA。

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

- 原始文字稿（口播脚本 / 逐字稿）可以临时保存在 `wx_channel/ref/{dna-id}/transcripts/`；也可以来自用户提供的任何位置，或由 Agent 转写后保存。
- 生成后的 DNA report 必须进入目标 DNA 的 `reports/` 目录。
- `sample-id` 必须可读且稳定；覆盖同名 report 前，先向用户说明该文件会被重算。

## 样本获取

视频号没有公开文案抓取路径，样本一律先落成文字稿再进 profiler：

| 来源 | 处理 |
| --- | --- |
| 用户提供口播脚本 / 逐字稿（`.md` / `.txt`） | 直接作为 profiler 输入 |
| 用户粘贴的文案、拆解笔记 | Agent 整理保存为 `.md` 再输入 |
| 本地视频文件（无文字稿） | 先用顶层 `talking-head-cut` ASR 转写拿逐字稿，保存为 `.md` 再输入；画面特征由 Agent 观看或用视觉模型抽帧补齐 |
| 抖音 / B站 / 小红书视频链接 | 走顶层 `viral-chaser` 下载 + 转写 + 拆解，产出拆解报告与逐字稿后作为输入（跨平台样本只借鉴结构，不照搬平台调性） |
| 视频号链接（`weixin.qq.com/sph/...`） | 无公开下载与文案路径：请用户提供文字稿或视频文件；自己账号的作品可用 `wx-channel-engagement list` 补描述文案与数据线索 |
| 自己账号的已发布作品 | `wx-channel-engagement list` 只能拿描述文案与行内指标；完整口播仍需转写或用户提供，描述文案不能冒充逐字稿 |
| `.docx` / 其他格式 | Agent 先提取为 `.md` / `.txt` 再进入 profiler |

处理样本时：

1. 剔除重复、已删除、纯搬运和无完整文案的样本。
2. 保留来源信息（视频链接、账号名、发布时间、获取时间）作为报告线索；链接拿不到时保留用户口述来源。
3. Profiler 本身不限制样本量；一个样本生成单篇 report，多个样本聚合统计。账号级初始化、老号诊断和对标比较可在 `account-setup.md` / `account-benchmark.md` 设置最低样本要求。
4. 播放、互动等数据只能来自用户提供或 `wx-channel-engagement`（仅限自己账号），不得编造。
5. 封面图优先用户提供的截图，或从视频文件抽帧截取；没有封面时保留缺失状态，不得用正文截图或想象补齐。

## 建立或重建 DNA

适用场景：目标 DNA 下还没有 report，或用户要求基于当前输入整体重建。

### Step 1 - 准备样本

把可用文字稿整理为 `.md` / `.txt`，并确定目标 `dna-id`。未指定时使用 `dna-0`。

### Step 2 - 生成单篇 report

每条视频执行一次：

```bash
wx-channel-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-video "https://weixin.qq.com/sph/xxxx"
```

可选参数：

- `--weight N`：用户明确强调某条参考价值时使用。
- `--focus DIMENSION`：用户明确说只借鉴钩子、文案、结构等局部时使用，可重复传入。

Agent 生成 scaffold 后必须回读文字稿，补齐 16 维单篇结论、脚本与画面证据、可复用信号，并补齐「视频信息」区（时长、形态、出镜占比、镜头字幕、BGM、数据线索——拿不到写未提供）；封面图维度必须由视觉模型读取本地封面图，输出可复现的 AIGC 提示词要素。

### Step 3 - 聚合 DNA

```bash
wx-channel-style-profiler build --dna-id {dna-id}
```

Agent 聚合时必须读取全部 report，结合权重、focus、高频共性、高权重偏好、孤例和例外，修订：

```text
wx_channel/dna/{dna-id}/{dna-id}.dna.md
wx_channel/dna/{dna-id}/{dna-id}.template.md
```

Template 聚合要求：

1. 开头两项固定为选题、标题（含封面图，视频号还包括短标题、描述文案与全局制作要求：时长与节奏、镜头与真人出镜、BGM 与音效）。
2. 脚本分段默认按五个语义部分输出：钩子、共情、信任状、价值、收尾；这是脚手架默认骨架，分段数量以 DNA 文档的结构结论为准，不为凑齐段数编造样本没有的规则。
3. 每个部分必须写入 DNA 文档中对应维度的执行要求，包括本段任务、切入或推进方式、句式、语气、素材、必须做和避免项。
4. 所有模板规则必须能从 DNA 文档推导。

多个样本时，定性结论必须说明覆盖多少条；单条特征只能写成单条观察，不得伪装成稳定共性。

## 更新已有 DNA

适用场景：目标 DNA 已存在，新增样本、偏好、局部借鉴或表现反馈。

### 新增样本

1. 先为新视频生成属于目标 DNA 的 report。
2. 再执行：

```bash
wx-channel-style-profiler update \
  --input wx_channel/dna/{dna-id}/reports/{sample-id}.report.md \
  --dna wx_channel/dna/{dna-id}/{dna-id}.dna.md \
  --template wx_channel/dna/{dna-id}/{dna-id}.template.md
```

3. Agent 根据新的加权统计和 16 维证据，同步修订 DNA 文档与 template。

### 用户偏好

用户意见不是直接入库的规则。Agent 必须先理解其指向，再转译到具体维度和执行要求，例如“开头冲突再前置一点”应落到前3秒钩子、开场节奏、口播语言等维度。

来自另一个 DNA 文档或 template 的局部结论，也按用户提供的参考要求处理：必须记录来源 `dna-id`、采纳范围、具体规则和冲突说明，再转译到当前 DNA 的对应维度与 template。它不要求重新抓取或重新提取原文。

可传入：

```bash
--user-input "结尾多用选择题引导评论"
```

转译结果写入 DNA 文档的“用户输入转译区”，并以可执行规则进入 template 的对应部分。原话不能成为 template 里的抽象口号。

### 局部借鉴

用户只希望借鉴某条的钩子、文案或结构时：

1. 为该视频生成目标 DNA 的 report。
2. 用 `--focus` 限定参与影响的维度。
3. 更新 DNA 文档与 template，并在报告中保留来源和 focus 说明。

### 表现反馈

来源：`content-calibrator` 的 DNA 表现评估报告（`wx_channel/dna/{dna-id}/evals/*.eval.md`）。评估回答「这个 DNA 好不好、哪些部分好/不好」，本 workflow 负责把**用户确认采纳**的评估结论转译进 DNA。

1. 前提：评估报告已存在，且用户逐条确认了要采纳的建议（未确认的建议不动 DNA）。
2. 每条采纳建议按参考输入处理：转译到具体维度和执行要求（如「分享率持续走低，内容缺社交价值」→ 转发动机设计 + 价值密度维度），经 `wx-channel-style-profiler update --user-input` 传入。
3. 转译结果写入 DNA 文档的「表现反馈区」（与「用户输入转译区」并列），每条记录：来源 eval 文件、affected dimensions、DNA 文档修改、template 修改。
4. 同步修订 template 对应部分；表现反馈只改规则表达，不引入样本未覆盖的新风格。
5. 趋势类证据（比值走向）只支持方向性调整（加强/弱化既有规则），不支持凭空新增维度规则——新增规则仍需样本或用户输入支撑。

## DNA 使用接口

本 Workflow 不描述如何用 DNA 生产：生产 workflow 自行读取 `wx_channel/dna/{dna-id}/{dna-id}.dna.md` 与 `{dna-id}.template.md`，按 template 执行，见 `content-production.md` / `editing.md`。

反馈回流判定：来自生产、改稿或复盘的成片/脚本修改意见，先判断是否可复用偏好——只有可复用偏好才经本 workflow「更新已有 DNA」进入 DNA；单次修改留在制作记录，不动 DNA。参考视频的风格吸收（“把这条的风格融入到我们的 DNA”）属于本 workflow 的新增样本 / 局部借鉴场景，不是生产流程的一部分。发布数据驱动的风格优化走「表现反馈」：`content-calibrator` 评估产出建议 → 用户逐条确认 → 本 workflow 转译进 DNA；评估本身不改 DNA。

## 对标接口

对标账号或一组对标视频不得默认落入现有 DNA；分析流程、逐项对比与采纳判断以 `account-benchmark.md` 为准。本 Workflow 只承担两件事：

1. 对标 DNA 的三层产物生成与更新：使用独立 `dna-id`（如 `dna-benchmark-{slug}`，同组后续更新复用），样本获取、report、build/update 同本 workflow 的创建/更新流程。
2. 用户采纳后，按「更新已有 DNA」执行并入基线 DNA 的更新：局部 DNA 融合、局部样本借鉴或偏好转译；默认优先局部 DNA 融合，不要求重新提取原文。

## 编排原则

- Workflow 负责选择路径和衔接工具，不复制 profiler 的 16 维定义。
- Agent 判断必须回读文字稿和 report，不能只依赖统计表。
- 样本统计描述内容模式，不替代事实核查、合规审核和商业判断。
- 用户确认只用于初始化方向或采纳建议，不是登记资产的前置门槛。
