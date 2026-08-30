# 抖音内容 DNA 创建与更新 Workflow

本 Workflow 只负责内容 DNA 三层产物的创建与更新：判断样本来源、选择目标 DNA、获取视频样本材料（`viral-chaser` 拆解）、调用 `douyin-style-profiler` 生成或更新 report / DNA 文档 / template。17 维提取与聚合方法以 `douyin-style-profiler` 为准（维度框架见其 `references/style-17d-framework.md`，初始版本已确认）。

边界说明：

- 账号初始化、定位梳理与默认 `dna-0` 初始化走 `account-setup.md`（该 workflow 会调用本 workflow 的样本获取与更新机制）。
- 账号对标分析走 `account-benchmark.md`；本 workflow 只承担对标 DNA 的三层产物生成与更新，以及采纳后并入基线 DNA 的更新。
- DNA 如何被用于内容生产（含仿照创作、素材组装、委托制作）由 `content-production.md` 规定，改片与文案调整由 `editing.md` 规定；本 workflow 不描述生产过程。

DNA 描述选题、钩子、口播表达、视觉制作、结构节奏与互动标记等内容规则；不描述发布操作与数据复盘。

## 入口判断

走本 Workflow：

- "建 DNA / 更新 DNA / 提炼这条视频的风格"
- "把这条视频落到某个 DNA 上"
- "提取下这个账号的内容 DNA"

不走本 Workflow：

- "帮我做条视频 / 照着这条仿一条 / 这个选题我们也做一条"（使用 DNA 生产）-> 走 `content-production.md`
- "改改这条的文案 / 重新剪一下" -> 走 `editing.md`
- "看数据 / 复盘 / 评估这个 DNA" -> 走 `review.md`
- "起号 / 梳理账号定位" -> 先走 `account-setup.md`
- "分析对标账号 / 对比风格差异" -> 走 `account-benchmark.md`

## 目标 DNA 选择

1. 用户明确指定 `dna-id` 时，使用该 DNA。
2. 用户明确说"落到默认 DNA"或未指定目标时，使用 `dna-0`。
3. 用户意图是账号对标、模式对比时，走 `account-benchmark.md`，对标样本必须进入独立 `dna-id`，不得直接写入 `dna-0`。
4. 找不到目标 DNA 文档时，先走 `account-setup.md` 建立 `dna-0`，或按用户明确指定的新 `dna-id` 初始化。

默认规则：

- 除 `account-benchmark.md` 分流的对标样本外，未特别分流的新参考视频累积到 `dna-0`。
- `dna-0` 不代表某个参考账号，而是当前工作区的默认内容生产规则集。
- 用户可以随时把样本、偏好或局部借鉴明确落到任意已有 DNA。

## 存储结构

```text
douyin/dna/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

- 原始转录文本可以临时保存在 `douyin/ref/{dna-id}/transcripts/`，也可以来自用户提供的路径。
- 生成后的 DNA report 必须进入目标 DNA 的 `reports/` 目录。
- `sample-id` 必须可读且稳定；覆盖同名 report 前，先向用户说明该文件会被重算。

## 样本获取

抖音样本的观测物是视频：口播转录、画面、封面、时长与互动线索。获取方式：

| 来源 | 处理 |
| --- | --- |
| 抖音视频链接（`v.douyin.com` / `www.douyin.com/video/...`） | self-spawn subagent 走 `viral-chaser` 拆解，产出转录全文、分句时间戳、时长、标题/描述/作者、互动计数与关键帧 |
| 用户提供的文字稿 / 脚本 / 口述要点 | Agent 整理为 `.md` / `.txt` 后直接作为 profiler 输入 |
| 本地视频文件 | 没有转录时请用户提供文字稿，或确认是否先委托转写；不得凭空编造转录 |
| 用户直接的想法 / 偏好 | 不生成 report，按"用户偏好"转译进入目标 DNA |

处理样本时：

1. `viral-chaser` 产物转成样本材料：转录全文（含标题、描述、作者、时长、互动数据线索）整理为一个转录 `.md`，标题写在一级标题；关键帧中的封面 / 首帧图（或封面下载图）作为 `--cover-image`。
2. 剔除重复、已删除、正文缺失或纯广告样本。
3. 保留来源 URL、作者、发布时间和获取时间作为报告线索。
4. Profiler 本身不限制样本量；一个样本生成单条 report，多个样本聚合统计。账号级初始化、老号诊断和对标比较可在 `account-setup.md` / `account-benchmark.md` 设置最低样本要求。
5. 互动数据（播放/点赞/评论/分享/收藏）只来自 `viral-chaser` 返回或用户提供的数据线索，不得编造；选样本时可参考互动信号，但数据好坏不直接等于风格好坏。
6. 封面 / 首帧缺失时保留缺失状态，不得用正文帧或想象补齐视觉证据。

## 建立或重建 DNA

适用场景：目标 DNA 下还没有 report，或用户要求基于当前输入整体重建。

### Step 1 - 准备样本

把可用视频整理为转录 `.md`（含封面 / 首帧图路径与时长），并确定目标 `dna-id`。未指定时使用 `dna-0`。

### Step 2 - 生成单条 report

每条视频执行一次：

```bash
douyin-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://www.douyin.com/video/..." \
  --duration 89
```

可选参数：

- `--weight N`：用户明确说某条参考价值非常高时使用。
- `--focus DIMENSION`：用户明确说只借鉴钩子、开头、结构等局部时使用，可重复传入。

Agent 生成 scaffold 后必须回读转录原文（必要时回看关键帧），补齐 17 维单条结论、原文证据和可复用信号；钩子维度必须逐字摘录前 3 秒口播 / 首帧字幕；封面 / 首帧维度必须由视觉模型读取本地图片，输出可复现的 AIGC 提示词要素。

### Step 3 - 聚合 DNA

```bash
douyin-style-profiler build --dna-id {dna-id}
```

Agent 聚合时必须读取全部 report，结合权重、focus、高频共性、高权重偏好、孤例和例外，修订：

```text
douyin/dna/{dna-id}/{dna-id}.dna.md
douyin/dna/{dna-id}/{dna-id}.template.md
```

Template 聚合要求：

1. 固定输出七个部分：选题、标题（含封面）、起、承、转、合、CTA。
2. 选题和标题保持 profiler 规定的形态（选题角度推荐、受众关联角度；标题类型、参考标题、话题标签策略、封面 / 首帧风格与 AIGC 提示词要素）。
3. 起、承、转、合、CTA 是固定语义部分（对应黄金开场、主体推进、高潮转折、收尾、互动引导），不是固定时长占比；每个部分可对应视频中的一个或多个段落。
4. 每个部分必须写入 DNA 文档中对应维度的执行要求，包括本段任务、执行方式、必须做和避免项。
5. 所有模板规则必须能从 DNA 文档推导；Agent 不得为了填满七部分而编造样本没有的规则。

多个样本时，定性结论必须说明覆盖多少条；单条特征只能写成单条观察，不得伪装成稳定共性。

## 更新已有 DNA

适用场景：目标 DNA 已存在，新增样本、偏好、局部借鉴或表现反馈。

### 新增样本

1. 先为新视频生成属于目标 DNA 的 report。
2. 再执行：

```bash
douyin-style-profiler update \
  --input douyin/dna/{dna-id}/reports/{sample-id}.report.md \
  --dna douyin/dna/{dna-id}/{dna-id}.dna.md \
  --template douyin/dna/{dna-id}/{dna-id}.template.md
```

3. Agent 根据新的加权统计和 17 维证据，同步修订 DNA 文档与 template。

### 用户偏好

用户意见不是直接入库的规则。Agent 必须先理解其指向，再转译到具体维度和执行要求，例如"开头冲突再前置一点"应落到 3秒钩子、视频结构模式、口播节奏等维度。

来自另一个 DNA 文档或 template 的局部结论，也按用户提供的参考要求处理：必须记录来源 `dna-id`、采纳范围、具体规则和冲突说明，再转译到当前 DNA 的对应维度与七部分 template。它不要求重新抓取或重新提取原视频。

可传入：

```bash
--user-input "开头冲突再前置一点"
```

转译结果写入 DNA 文档的"用户输入转译区"，并以可执行规则进入 template 的对应部分。原话不能成为 template 里的抽象口号。

### 局部借鉴

用户只希望借鉴某条视频的钩子、开头或结构时：

1. 为该视频生成目标 DNA 的 report。
2. 用 `--focus` 限定参与影响的维度。
3. 更新 DNA 文档与 template，并在报告中保留来源和 focus 说明。

### 表现反馈

来源：`content-calibrator` 的 DNA 表现评估报告（`douyin/dna/{dna-id}/evals/*.eval.md`）。评估回答"这个 DNA 好不好、哪些部分好/不好"，本 workflow 负责把**用户确认采纳**的评估结论转译进 DNA。

1. 前提：评估报告已存在，且用户逐条确认了要采纳的建议（未确认的建议不动 DNA）。
2. 每条采纳建议按参考输入处理：转译到具体维度和执行要求（如"播放稳定但评论持续走低，结尾提问太泛"→ 互动设计维度 + CTA 部分表达方式），经 `douyin-style-profiler update --user-input` 传入。
3. 转译结果写入 DNA 文档的「表现反馈区」（与「用户输入转译区」并列），每条记录：来源 eval 文件、affected dimensions、DNA 文档修改、template 修改。
4. 同步修订 template 对应部分；表现反馈只改规则表达，不引入样本未覆盖的新风格。
5. 趋势类证据（比值走向）只支持方向性调整（加强/弱化既有规则），不支持凭空新增维度规则——新增规则仍需样本或用户输入支撑。

## DNA 使用接口

本 Workflow 不描述如何用 DNA 生产：生产 workflow 自行读取 `douyin/dna/{dna-id}/{dna-id}.dna.md` 与 `{dna-id}.template.md`，按 template 七部分执行，见 `content-production.md` / `editing.md`。

反馈回流判定：来自生产、改片或复盘的成品修改意见，先判断是否可复用偏好——只有可复用偏好才经本 workflow「更新已有 DNA」进入 DNA；单次修改留在稿件审阅记录，不动 DNA。参考视频的风格吸收（"把这条的风格融入到我们的 DNA"）属于本 workflow 的新增样本 / 局部借鉴场景，不是生产流程的一部分。发布数据驱动的风格优化走「表现反馈」：`content-calibrator` 评估产出建议 → 用户逐条确认 → 本 workflow 转译进 DNA；评估本身不改 DNA。

## 对标接口

对标账号或一组对标视频不得默认落入现有 DNA；分析流程、逐项对比与采纳判断以 `account-benchmark.md` 为准。本 Workflow 只承担两件事：

1. 对标 DNA 的三层产物生成与更新：使用独立 `dna-id`（如 `dna-benchmark-{slug}`，同组后续更新复用），样本获取、report、build/update 同本 workflow 的创建/更新流程。
2. 用户采纳后，按「更新已有 DNA」执行并入基线 DNA 的更新：局部 DNA 融合、局部样本借鉴或偏好转译；默认优先局部 DNA 融合，不要求重新提取原视频。

## 编排原则

- Workflow 负责选择路径和衔接工具，不复制 profiler 的 17 维定义。
- Agent 判断必须回读转录原文和 report，不能只依赖统计表。
- 样本统计描述内容模式，不替代事实核查、合规审核和商业判断。
- 用户确认只用于初始化方向或采纳建议，不是登记资产的前置门槛。
