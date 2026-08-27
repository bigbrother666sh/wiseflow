---
name: xhs-style-profiler
description: 为单篇小红书笔记提取 16 维 DNA report，按 DNA ID 聚合历史 report 生成 DNA 文档，并推导完整的 DNA template。
metadata:
  openclaw:
    emoji: 🧬
---

# xhs-style-profiler

小红书图文笔记的内容风格提取与 DNA 生产工具。输入是**笔记的文本材料**（标题 + 正文 + 内联话题标签，由 Agent 先行整理成 `.md` / `.txt`）与封面图；不接受笔记链接或图片文件直接作为主输入（链接先用 `xhs-content-ops` 下载，图片作为 `--cover-image` 或视觉证据进入）。

## 产物模型

```text
单篇笔记 -> DNA report
同一个 DNA 目录下的全部 report + 权重/focus -> DNA 文档
DNA 文档 -> DNA template
```

- **DNA report**：单篇笔记的 16 维提取结果。
- **DNA 文档**：聚合历史 report 后得到的内容与风格规则。
- **DNA template**：由 DNA 文档推导出的生产模板，供生产时直接执行。

## 存储结构

DNA 以 DNA ID 为主体存储，一个 DNA 可以持续放入任意数量笔记，样本可以来自一个或多个参考账号，甚至来自用户直接的想法。

```text
dna/xhs/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

原始笔记文本可以临时来自任何位置（建议 `xhs_ref/{dna-id}/notes/`）；生成后的 DNA report 必须进入对应 DNA 的 `reports/` 目录。

## 样本文件约定

```markdown
# 笔记标题（首个一级标题行，≤20 字）
正文第 1-2 行（开头钩子）

正文主体段落……
空行分段，保留原有换行节奏与 emoji。

#话题1 #话题2 #话题3
```

- 首个 `# ` 一级标题行被识别为笔记标题，其余内容为正文。
- 正文保持纯文本，不使用 markdown 小标题，避免与话题标签的 `#` 混淆。
- 话题标签按小红书原样以 `#话题` 内联，脚本按它统计标签数。
- 视频笔记样本必须先用 `viral-chaser` 拆解出转录与封面，再整理成本格式文本输入；本工具不解析视频。

## 职责边界

- 输入笔记文本支持 `.md` / `.txt`；笔记链接、图片不直接作为主输入。
- 统计只作为聚合证据底座，不评分、不替代定性判断。
- 16 维语义判断由 Agent 回读笔记原文完成；封面与图组维度必须由视觉模型读取本地图片完成。
- 不输出选题价值判断、合规结论、账号权重或风格评分。
- 不要求用户确认或登记 INDEX。

## Report - 单篇提取

```bash
xhs-style-profiler report \
  --input path/to/note.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://www.xiaohongshu.com/explore/..."
```

默认输出：

```text
dna/xhs/{dna-id}/reports/{sample-id}.report.md
```

参数说明：

- `--cover-image`：封面本地图片（`xhs-content-ops` 下载的首图或用户提供的封面），进入视觉模型分析。
- `--source-url`：原笔记链接，作为报告证据保留；本地原创素材无链接时省略。

可配置权重：

```bash
--weight 3
```

可限制该篇只在某些维度参与借鉴：

```bash
--focus opening-hook
--focus cover-imageset
```

Agent 生成 scaffold 后必须回读笔记原文，补齐每个维度的单篇结论、原文证据和可复用创作信号；开头钩子维度必须逐字摘录正文前 1-2 行。
封面与图组维度必须读取 `--cover-image` 指向的本地图片（图组其余图片如有路径一并读取），并通过视觉模型补齐封面承诺、版式、构图、色彩、文字视觉、风格一致性、品牌元素、避免项和 AIGC 复现提示词要素。没有图片时记录"未提供"，不得编造。

## Build - 聚合 DNA 文档与模板

```bash
xhs-style-profiler build --dna-id {dna-id}
```

默认读取：

```text
dna/xhs/{dna-id}/reports/
```

默认输出：

```text
dna/xhs/{dna-id}/{dna-id}.dna.md
dna/xhs/{dna-id}/{dna-id}.template.md
```

也可显式传入一个或多个 report 文件/目录：

```bash
xhs-style-profiler build \
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

Template 是生产模板，不是概念解释。必须从 DNA 文档的 16 个维度推导，至少包含：

- 选题角度、受众关系
- 标题类型、参考标题、话题标签策略、封面图风格和封面 AIGC 提示词要素
- 开头、承、结尾、CTA、图组五个语义部分（对应笔记的开头钩子、正文主体、收束、互动引导、图片轨道）
- 每个部分的本段任务、执行方式和必须做 / 避免项

模板整体固定为七个部分：选题、标题（含封面图）、开头、承、结尾、CTA、图组。固定的是语义结构，不是字数占比；任一部分可以对应笔记中的一段或多段文字、一张或多张图片，也可以在特定内容形态下弱化。

五个笔记部分必须充分吸收 DNA 文档中的维度结论：

| 部分 | 主要推导来源 |
| --- | --- |
| 开头 | 开头钩子、选题角度、标题风格、口语语气与人设 |
| 承 | 正文结构、口语语气与人设、emoji与标点节奏、证据与人味、关键词与搜索流量 |
| 结尾 | 签名式标记、口语语气与人设、系列化设计 |
| CTA | 互动设计、行动引导与转化、话题标签策略 |
| 图组 | 封面与图组、图片构图与信息、视觉风格、证据与人味 |

## Update - 增量聚合

```bash
xhs-style-profiler update \
  --input dna/xhs/{dna-id}/reports/{new-sample}.report.md \
  --dna dna/xhs/{dna-id}/{dna-id}.dna.md \
  --template dna/xhs/{dna-id}/{dna-id}.template.md
```

脚本会合并 DNA 文档记录的历史 report 与新 report，重新计算加权统计，并保留 Agent 已完成内容。Agent 仍需重新审视聚合结论，再同步修订 DNA 文档和 template。

`--input` 可省略。省略时表示没有新增样本，只基于历史 report、既有 DNA 文档和用户输入做融合；适用于采纳另一个 DNA 文档或 template 中的局部规则。此时仍必须通过 `--user-input` 传入要融合的要求，并由 Agent 转译到具体维度。

## 用户输入转译

用户输入是参考信息，不是可直接入库的 DNA 规则。

```bash
--user-input "开头钩子再直接一点，第一行就给出收益"
```

Agent 必须把输入转译到具体维度，例如：

```text
opening-hook：钩子改为结果前置，第一行直接给收益数字
body-structure：开头两行均为短句，不做背景铺垫
title-style：标题同步采用结果前置型
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
| `title-style` | 标题风格 |
| `cover-imageset` | 封面与图组 |
| `keyword-seo` | 关键词与搜索流量 |
| `opening-hook` | 开头钩子 |
| `body-structure` | 正文结构 |
| `language-tone` | 口语语气与人设 |
| `emoji-rhythm` | emoji与标点节奏 |
| `image-composition` | 图片构图与信息 |
| `visual-style` | 视觉风格 |
| `credibility-proof` | 证据与人味 |
| `interaction-design` | 互动设计 |
| `tag-strategy` | 话题标签策略 |
| `cta-conversion` | 行动引导与转化 |
| `signature-mark` | 签名式标记 |
| `series-design` | 系列化设计 |

## 统计与分词

脚本统计笔记文本的标题字数、句段、行数、标点、人称、emoji、话题标签等指标；中文高频信号使用相邻二字组合，仅作为候选线索。Agent 必须回读原文判断它是否真是口头禅或签名式表达。

当前不引入 jieba。若后续候选噪声明显，可把 jieba 作为候选词挖掘器加入仓库级依赖，但分词结果不能直接作为 DNA 结论。

## 参考资料

- `references/xhs-note-dna-dimensions.md`（小红书 16 维 DNA 分析框架，v0 初始版本，2026-08-28 用户确认）
