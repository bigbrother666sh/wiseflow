---
name: douyin-style-profiler
description: 为单条抖音视频提取 17 维 DNA report，按 DNA ID 聚合历史 report 生成 DNA 文档，并推导完整的 DNA template。
---

# douyin-style-profiler

抖音短视频的内容风格提取与 DNA 生产工具。输入是**视频的转录文本**（口播转录全文 + 标题/描述/时长/互动线索，由 Agent 先行整理成 `.md` / `.txt`）与封面 / 首帧图；不接受视频文件或视频链接作为输入。

## 产物模型

```text
单条视频 -> DNA report
同一个 DNA 目录下的全部 report + 权重/focus -> DNA 文档
DNA 文档 -> DNA template
```

- **DNA report**：单条视频的 17 维提取结果。
- **DNA 文档**：聚合历史 report 后得到的内容与风格规则。
- **DNA template**：由 DNA 文档推导出的生产模板，供生产时直接执行。

## 存储结构

DNA 以 DNA ID 为主体存储，一个 DNA 可以持续放入任意数量视频，样本可以来自一个或多个参考账号，甚至来自用户直接的想法。

```text
douyin/dna/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

原始转录文本可以临时来自任何位置（建议 `douyin/ref/{dna-id}/transcripts/`）；生成后的 DNA report 必须进入对应 DNA 的 `reports/` 目录。

## 职责边界

- 输入转录文本支持 `.md` / `.txt`；视频文件、链接不直接作为输入。
- 统计只作为聚合证据底座，不评分、不替代定性判断。
- 17 维语义判断由 Agent 回读转录原文（必要时回看视频关键帧）完成；封面 / 首帧维度必须由视觉模型读取本地图片完成。
- 不输出选题价值判断、合规结论、账号权重或风格评分。
- 不要求用户确认或登记 INDEX。

## Report - 单条提取

```bash
douyin-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://www.douyin.com/video/..." \
  --duration 89
```

默认输出：

```text
douyin/dna/{dna-id}/reports/{sample-id}.report.md
```

参数说明：

- `--cover-image`：封面或首帧本地图片（抽帧产物或封面下载图），进入视觉模型分析。
- `--source-url`：原视频链接，作为报告证据保留；本地素材无链接时省略。
- `--duration`：视频时长（秒），用于口播密度统计；未知时省略。

可配置权重：

```bash
--weight 3
```

可限制该条只在某些维度参与借鉴：

```bash
--focus hook
--focus speech-rhythm
```

Agent 生成 scaffold 后必须回读转录原文，补齐每个维度的单条结论、原文证据和可复用创作信号；钩子维度必须逐字摘录前 3 秒口播 / 首帧字幕。
封面 / 首帧维度必须读取 `--cover-image` 指向的本地图片，并通过视觉模型补齐主体、构图、色彩、光线、质感、风格、文字视觉、品牌元素、避免项和 AIGC 复现提示词要素。没有图片时记录"未提供"，不得编造。

## Build - 聚合 DNA 文档与模板

```bash
douyin-style-profiler build --dna-id {dna-id}
```

默认读取：

```text
douyin/dna/{dna-id}/reports/
```

默认输出：

```text
douyin/dna/{dna-id}/{dna-id}.dna.md
douyin/dna/{dna-id}/{dna-id}.template.md
```

也可显式传入一个或多个 report 文件/目录：

```bash
douyin-style-profiler build \
  --input path/to/reports \
  --dna-id {dna-id}
```

Agent 聚合时必须：

1. 读取全部 DNA report，不能只看统计表。
2. 按每个 report 的 `weight` 和 `focus` 判断影响范围。
3. 区分高频共性、高权重偏好、局部借鉴、孤例和例外。
4. 为每个维度写聚合结论、报告依据和创作规则。
5. 确保 DNA 文档能够完整推导 template。

## DNA Template

Template 是生产模板，不是概念解释。必须从 DNA 文档的 17 个维度推导，至少包含：

- 选题角度、受众关系
- 标题类型、参考标题、话题标签策略、封面 / 首帧风格和封面 AIGC 提示词要素
- 起、承、转、合、CTA 五个固定语义部分（对应短视频的黄金开场、主体推进、高潮转折、收尾、互动引导）
- 每个部分的本段任务、执行方式和必须做 / 避免项

模板整体固定为七个部分：选题、标题（含封面）、起、承、转、合、CTA。固定的是语义结构，不是物理时长占比；任一部分可以对应视频中的一个或多个段落，也可以在特定内容形态下弱化。

五个视频部分必须充分吸收 DNA 文档中的维度结论：

| 部分 | 主要推导来源 |
| --- | --- |
| 起 | 3秒钩子、选题角度、口播节奏、语气与人设感、镜头语言 |
| 承 | 视频结构模式、叙事节奏、口播节奏、用词习惯、专业度体现、镜头语言 |
| 转 | 冲突与张力、叙事节奏、情绪表达（语气与人设感）、口播节奏 |
| 合 | 视频结构模式、签名式标记、语气与人设感、系列化与合集 |
| CTA | 互动设计、选题与受众关联、语气与人设感 |

## Update - 增量聚合

```bash
douyin-style-profiler update \
  --input douyin/dna/{dna-id}/reports/{new-sample}.report.md \
  --dna douyin/dna/{dna-id}/{dna-id}.dna.md \
  --template douyin/dna/{dna-id}/{dna-id}.template.md
```

脚本会合并 DNA 文档记录的历史 report 与新 report，重新计算加权统计，并保留 Agent 已完成内容。Agent 仍需重新审视聚合结论，再同步修订 DNA 文档和 template。

`--input` 可省略。省略时表示没有新增样本，只基于历史 report、既有 DNA 文档和用户输入做融合；适用于采纳另一个 DNA 文档或 template 中的局部规则。此时仍必须通过 `--user-input` 传入要融合的要求，并由 Agent 转译到具体维度。

## 用户输入转译

用户输入是参考信息，不是可直接入库的 DNA 规则。

```bash
--user-input "开头冲突再前置一点"
```

Agent 必须把输入转译到具体维度，例如：

```text
hook：钩子改为矛盾前置，第一句直接给反差结果
video-structure：开场压缩到 2 秒内进入冲突画面
speech-rhythm：开场两句均为短句，不做背景铺垫
```

处理要求：

1. 在 DNA 文档的"用户输入转译区"记录 affected dimensions、DNA 修改和 template 修改。
2. 把原话转译成可执行的聚合结论与创作规则。
3. Template 只写转译后的执行规则，不直接抄用户原话。
4. 与样本证据冲突时保留冲突说明，由用户选择优先级。

## Focus ID

| ID | 维度 |
|---|---|
| `topic-angle` | 选题角度 |
| `title-style` | 标题与文案 |
| `cover-frame` | 封面与首帧 |
| `hook` | 3秒钩子 |
| `word-habit` | 用词习惯 |
| `speech-rhythm` | 口播节奏 |
| `tone` | 语气与人设感 |
| `shot-language` | 镜头语言 |
| `visual-style` | 画面风格 |
| `sound-design` | 声音与BGM |
| `video-structure` | 视频结构模式 |
| `narrative-rhythm` | 叙事节奏 |
| `conflict-tension` | 冲突与张力 |
| `professionalism` | 专业度体现 |
| `interaction-design` | 互动设计 |
| `signature` | 签名式标记 |
| `series-design` | 系列化与合集 |

## 统计与分词

脚本统计转录文本的句段、标点、人称、口播密度（需 `--duration`）等指标；中文高频信号使用相邻二字组合，仅作为候选线索。Agent 必须回读原文判断它是否真是口头禅或签名式表达。

当前不引入 jieba。若后续候选噪声明显，可把 jieba 作为候选词挖掘器加入仓库级依赖，但分词结果不能直接作为 DNA 结论。

## 参考资料

- `references/style-17d-framework.md`（抖音 17 维 DNA 分析框架，初始版本已确认）
