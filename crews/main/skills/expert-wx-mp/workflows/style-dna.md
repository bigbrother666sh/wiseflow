# 公众号内容 DNA 编排 Workflow

本 Workflow 只负责编排：判断样本来源、选择目标 DNA、调用 `wx-mp-hunter` 获取材料、调用 `wechat-style-profiler` 生成或更新三层产物。16 维提取与聚合方法以 `tools/wechat-style-profiler/` 为准。

DNA 只描述选题、标题、内容结构与表达策略。排版由 `generate-wenyan-theme` 独立管理，不参与 DNA 采样、组合或评分。

## 入口判断

走本 Workflow：

- “建 DNA / 更新 DNA / 提炼文章风格”
- “把这篇文章落到某个 DNA 上”
- “按这个风格写，但没有现成 DNA”

不走本 Workflow：

- “照着这篇排版” -> 走 `generate-wenyan-theme`
- “只换颜色 / 字体 / 间距” -> 走 `generate-wenyan-theme`
- “起号 / 梳理账号定位” -> 先走 `account-setup.md`
- “分析对标账号 / 对比风格差异” -> 走 `account-benchmark.md`

## 目标 DNA 选择

1. 用户明确指定 `dna-id` 时，使用该 DNA。
2. 用户明确说“落到默认 DNA”或未指定目标时，使用 `dna-0`。
3. 用户意图是账号对标、模式对比时，走 `account-benchmark.md`，对标样本必须进入独立 `dna-id`，不得直接写入 `dna-0`。
4. 找不到目标 DNA 文档时，先走 `account-setup.md` 建立 `dna-0`，或按用户明确指定的新 `dna-id` 初始化。

默认规则：

- 除 `account-benchmark.md` 分流的对标样本外，未特别分流的新参考文章累积到 `dna-0`。
- `dna-0` 不代表某个参考账号，而是当前工作区的默认内容生产规则集。
- 用户可以随时把样本、偏好或局部借鉴明确落到任意已有 DNA。

## 存储结构

```text
dna/wx_mp/{dna-id}/
  reports/
    {sample-id}.report.md
  {dna-id}.dna.md
  {dna-id}.template.md
```

- 原始文章可以临时保存在 `wx_mp_ref/{dna-id}/articles/`，也可以来自用户提供的路径。
- 生成后的 DNA report 必须进入目标 DNA 的 `reports/` 目录。
- 不登记 `INDEX.md`，不生成 `.metrics.json`，不生成 `.evaluation.md`。
- `sample-id` 必须可读且稳定；覆盖同名 report 前，先向用户说明该文件会被重算。

## 样本获取

按来源选择获取方式：

| 来源 | 处理 |
| --- | --- |
| `mp.weixin.qq.com` 文章链接 | 调 `wx-mp-hunter fetch <url>` 获取正文 |
| 公众号名称 | 调 `wx-mp-hunter posts-list` 获取可访问列表，再按需 `fetch`；抓不到时请用户提供链接 |
| 专题页 / 合集页 | 调 `wx-mp-hunter homepage` 获取链接后逐篇 `fetch` |
| 本地 `.md` / `.txt` | 直接作为 profiler 输入 |
| `.docx` / 粘贴文本 | Agent 先提取或保存为 `.md` / `.txt`，再进入 profiler |

处理样本时：

1. 剔除重复、删除、付费不可读、正文缺失或非文章页面。
2. 保留来源 URL、账号名、发布时间和获取时间作为报告线索。
3. Profiler 本身不限制样本量；一个样本生成单篇 report，多个样本聚合统计。账号级初始化、老号诊断和对标比较可在 `account-setup.md` / `account-benchmark.md` 设置最低样本要求；低于该要求时仍可生成 report，但结论必须降级为单篇或小样本观察，不得称为账号级稳定 DNA。
4. `wx-mp-hunter` 不提供阅读、转发、评论等互动数据；如需用互动信号选样本，只能依赖用户提供的截图或数据，不得编造。

## 建立或重建 DNA

适用场景：目标 DNA 下还没有 report，或用户要求基于当前输入整体重建。

### Step 1 - 准备样本

把可用文章整理为 `.md` / `.txt`，并确定目标 `dna-id`。未指定时使用 `dna-0`。

### Step 2 - 生成单篇 report

每篇文章执行一次：

```bash
wechat-style-profiler report \
  --input path/to/article.md \
  --dna-id {dna-id} \
  --sample-id {sample-id}
```

可选参数：

- `--weight N`：用户明确强调某篇参考价值时使用。
- `--focus DIMENSION`：用户明确说只借鉴标题、结构、语气等局部时使用，可重复传入。

Agent 生成 scaffold 后必须回读原文，补齐 16 维单篇结论、原文证据和可复用信号。

### Step 3 - 聚合 DNA

```bash
wechat-style-profiler build --dna-id {dna-id}
```

Agent 聚合时必须读取全部 report，结合权重、focus、高频共性、高权重偏好、孤例和例外，修订：

```text
dna/wx_mp/{dna-id}/{dna-id}.dna.md
dna/wx_mp/{dna-id}/{dna-id}.template.md
```

Template 聚合要求：

1. 固定输出七个部分：选题、标题、起、承、转、合、CTA。
2. 选题和标题保持 profiler 规定的两行形态。
3. 起、承、转、合、CTA 是固定语义部分，不是固定物理段落数；每个部分可对应一个或多个自然段。
4. 每个部分必须写入 DNA 文档中对应维度的执行要求，包括本段任务、切入或推进方式、结构、句式、语气、素材、必须做和避免项。
5. 所有模板规则必须能从 DNA 文档推导；Agent 不得为了填满七部分而编造样本没有的规则。

多个样本时，定性结论必须说明覆盖多少篇；单篇特征只能写成单篇观察，不得伪装成稳定共性。

## 更新已有 DNA

适用场景：目标 DNA 已存在，用户新增样本、偏好或局部借鉴。

### 新增样本

1. 先为新文章生成属于目标 DNA 的 report。
2. 再执行：

```bash
wechat-style-profiler update \
  --input dna/wx_mp/{dna-id}/reports/{sample-id}.report.md \
  --dna dna/wx_mp/{dna-id}/{dna-id}.dna.md \
  --template dna/wx_mp/{dna-id}/{dna-id}.template.md
```

3. Agent 根据新的加权统计和 16 维证据，同步修订 DNA 文档与 template。

### 用户偏好

用户意见不是直接入库的规则。Agent 必须先理解其指向，再转译到具体维度和执行要求，例如“短句比例提升”应落到句式节奏、词汇句式、段落微操等维度。

来自另一个 DNA 文档或 template 的局部结论，也按用户提供的参考要求处理：必须记录来源 `dna-id`、采纳范围、具体规则和冲突说明，再转译到当前 DNA 的对应维度与七部分 template。它不要求重新抓取或重新提取原文。

可传入：

```bash
--user-input "短句比例提升"
```

转译结果写入 DNA 文档的“用户输入转译区”，并以可执行规则进入 template 的对应部分。原话不能成为 template 里的抽象口号。

### 局部借鉴

用户只希望借鉴某篇的标题、开头或结构时：

1. 为该文章生成目标 DNA 的 report。
2. 用 `--focus` 限定参与影响的维度。
3. 更新 DNA 文档与 template，并在报告中保留来源和 focus 说明。

## 使用 DNA

生产前读取：

```text
dna/wx_mp/{dna-id}/{dna-id}.dna.md
dna/wx_mp/{dna-id}/{dna-id}.template.md
```

使用规则：

1. Template 是直接生产模板，按选题、标题、起、承、转、合、CTA 七部分执行；DNA 文档解释依据、稳定性和例外。
2. 用户对某次成稿提出风格修改意见时，先判断是否需要更新 DNA；只有可复用偏好才进入 DNA，单次修改留在稿件审阅记录中。
3. 不运行旧版 DNA 评分，不以排版变化作为 DNA 符合证据。

## 账号对标

对标账号或一组对标文章不得默认落入现有 DNA。处理顺序：

1. 读取 `account-benchmark.md`。
2. 为同一对标对象或样本组使用独立 `dna-id`，例如 `dna-benchmark-{slug}`；同组后续更新复用该 DNA，不重复新建。
3. 生成单篇 report，聚合 DNA 文档与 template。
4. 与 `dna-0` 或用户指定 DNA 做逐项对比。
5. 用户确认采纳时，按 `account-benchmark.md` Step 5 选择局部 DNA 融合、局部样本借鉴或偏好转译；默认优先局部 DNA 融合，不要求重新提取原文。

## 编排原则

- Workflow 负责选择路径和衔接工具，不复制 profiler 的 16 维定义。
- Agent 判断必须回读原文和 report，不能只依赖统计表。
- 样本统计描述内容模式，不替代事实核查、合规审核和商业判断。
- 用户确认只用于初始化方向或采纳建议，不是登记资产的前置门槛。
