---
name: wx-channel-style-profiler
description: 为单条视频号视频提取 16 维 DNA report，按 DNA ID 聚合历史 report 生成 DNA 文档，并推导完整的 DNA template。
metadata:
  openclaw:
    emoji: 🧬
---

# wx-channel-style-profiler

> **维度版本 v0**（2026-08-27 用户确认）：16 维划分、命名与 focus ID 见 `references/video-dna-dimensions.md`。调整维度需升版本并同步脚本 `DIMENSION_GROUPS` 与下方 Focus ID 表。

## 产物模型

```text
单条视频 -> DNA report
同一个 DNA 目录下的全部 report + 权重/focus -> DNA 文档
DNA 文档 -> DNA template
```

- **DNA report**：单条视频的 16 维提取结果。
- **DNA 文档**：聚合历史 report 后得到的风格与选题规则。
- **DNA template**：由 DNA 文档推导出的创作模板，供视频生产时直接执行。

## 存储结构

DNA 以 DNA ID 为主体存储，一个 DNA 可以持续放入任意数量视频样本，样本可以来自一个或多个账号，甚至来自用户提供的脚本想法。

```text
dna/wx_channel/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

原始资料（口播脚本 / 逐字稿文本）可以临时来自任何位置；生成后的 DNA report 必须进入对应 DNA 的 `reports/` 目录。

## 职责边界

- 输入正文支持 `.md` / `.txt` 的口播脚本或逐字稿；视频文件本身不是本工具输入，Agent 先取得文字稿（ASR 转写、用户提供或拆解报告整理）再进入本工具。
- 统计只作为聚合证据底座，不评分、不替代定性判断。
- 16 维语义判断由 Agent 回读脚本与原视频信息完成；封面图维度必须由视觉模型读取本地图片完成。
- 不输出合规结论、账号权重或风格评分。
- 不要求用户确认或登记 INDEX。

## Report - 单条提取

```bash
wx-channel-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-video "https://weixin.qq.com/sph/xxxx"
```

默认输出：

```text
dna/wx_channel/{dna-id}/reports/{sample-id}.report.md
```

可配置权重：

```bash
--weight 3
```

可限制该条只在某些维度参与借鉴：

```bash
--focus hook-design
--focus narration-language
```

`--source-video` 可选：记录源视频链接或本地路径，仅写入 frontmatter 备查。

Agent 生成 scaffold 后必须回读脚本原文，补齐每个维度的单条结论、脚本与画面证据和可复用创作信号，并补齐「视频信息」区（时长、形态、出镜占比、镜头字幕、BGM、数据线索——拿不到的写未提供，不得编造）。
封面图维度必须读取 `--cover-image` 指向的本地图片，并通过视觉模型补齐主体、构图、色彩、光线、质感、风格、文字视觉（含封面三要素：身份/痛点/方案）、品牌元素、避免项和 AIGC 复现提示词要素。没有封面图时记录“未提供”，不得编造。

## Build - 聚合 DNA 文档与模板

```bash
wx-channel-style-profiler build --dna-id {dna-id}
```

默认读取：

```text
dna/wx_channel/{dna-id}/reports/
```

默认输出：

```text
dna/wx_channel/{dna-id}/{dna-id}.dna.md
dna/wx_channel/{dna-id}/{dna-id}.template.md
```

也可显式传入一个或多个 report 文件/目录：

```bash
wx-channel-style-profiler build \
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

Template 是创作模板，不是概念解释。必须从 DNA 文档的 16 个维度推导，至少包含：

- 选题角度、受众关系
- 标题类型、参考标题、短标题与描述文案规则、封面图风格和封面 AIGC 提示词要素
- 全局制作要求：时长与节奏、镜头与真人出镜、BGM 与音效
- 钩子、共情、信任状、价值、收尾五个默认语义部分
- 每个部分的本段任务、推进方式、句式、语气、素材、必须做和避免项

开头两项（选题、标题（含封面图与描述文案））跨平台通用；五个语义部分是脚手架默认骨架，来自视频号通用脚本结构（3 秒钩子 → 痛点 → 信任状 → 价值 → 收尾），分段数量最终以 DNA 文档的结构结论为准，不为凑齐五段而编造规则。

五个部分必须充分吸收 DNA 文档中的维度结论：

| 部分 | 主要推导来源 |
| --- | --- |
| 钩子 | 前3秒钩子、开场节奏与身份信号、选题角度、口播语言 |
| 共情 | 脚本结构、口播语言、语气与人设基调、选题角度 |
| 信任状 | 信任状、语气与人设基调、签名式标记 |
| 价值 | 价值密度、画面与节奏、时长与形态、脚本结构 |
| 收尾 | 收尾与转化、互动设计、转发动机设计、语气与人设基调 |

## Update - 增量聚合

```bash
wx-channel-style-profiler update \
  --input dna/wx_channel/{dna-id}/reports/{new-sample}.report.md \
  --dna dna/wx_channel/{dna-id}/{dna-id}.dna.md \
  --template dna/wx_channel/{dna-id}/{dna-id}.template.md
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
hook-design：第一句直接抛反常识结论，身份介绍后移
opening-pace：前 2 秒完成冲突，第 3 秒预告价值
narration-language：钩子句控制在 15 字以内的短句
```

处理要求：

1. 在 DNA 文档的“用户输入转译区”记录 affected dimensions、DNA 修改和 template 修改。
2. 把原话转译成可执行的聚合结论与创作规则。
3. Template 只写转译后的执行规则，不直接抄用户原话。
4. 与样本证据冲突时保留冲突说明，由用户选择优先级。

## Focus ID

| ID | 维度 |
|---|---|
| `topic-angle` | 选题角度 |
| `title-desc` | 标题与描述文案 |
| `cover-image` | 封面图 |
| `hook-design` | 前3秒钩子 |
| `opening-pace` | 开场节奏与身份信号 |
| `narration-language` | 口播语言 |
| `tone-persona` | 语气与人设基调 |
| `signature-expression` | 签名式标记 |
| `script-structure` | 脚本结构 |
| `visual-pacing` | 画面与节奏 |
| `duration-form` | 时长与形态 |
| `credibility-proof` | 信任状 |
| `value-density` | 价值密度 |
| `interaction-design` | 互动设计 |
| `share-motive` | 转发动机设计 |
| `cta-funnel` | 收尾与转化 |

## 统计与分词

脚本统计口播脚本的句段、标点、人称等指标；中文高频信号使用相邻二字组合，仅作为候选线索。Agent 必须回读原文判断它是否真是口头禅或签名式表达。时长、镜头、出镜占比等视频观测不在文本统计范围内，由 Agent 补齐「视频信息」区。

当前不引入 jieba。若后续候选噪声明显，可把 jieba 作为候选词挖掘器加入仓库级依赖，但分词结果不能直接作为 DNA 结论。

## 参考资料

- `references/video-dna-dimensions.md`（16 维 v0 定稿与 template 分段说明）
