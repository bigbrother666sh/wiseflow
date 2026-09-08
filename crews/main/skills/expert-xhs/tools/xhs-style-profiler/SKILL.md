---
name: xhs-style-profiler
description: 提取小红书账号级 DNA：单篇笔记生成 report，聚合定位、选题、标题、图文视频比例、发布节奏、高数据创意、搜索关键词与用户问题，推导 main agent 的图文生产输入或视频 Brief template。
metadata:
  openclaw:
    emoji: 🧬
---

# xhs-style-profiler

小红书账号级 DNA 提取与聚合工具。输入是**笔记文本材料**（标题 + 正文 + 内联话题标签，由 Agent 先整理成 `.md` / `.txt`）与可选封面图；不接受笔记链接或图片文件作为直接输入。链接先用 `xhs-content-ops` 下载，图片作为视觉证据进入。

DNA 的用途是指导 main agent 图文笔记生产、搜索意图覆盖和视频制作 Brief；不指导 main agent 直接产出全片。

## 产物模型

```text
单篇笔记 -> DNA report
同一 DNA 下的全部 report + 权重/focus + 用户输入 -> DNA 文档
DNA 文档 -> 图文生产输入 / 视频制作 Brief template
```

- **DNA report**：单篇样本的账号级观测与 14 维提取结果。
- **DNA 文档**：聚合后的账号级规则、搜索意图地图与样本覆盖度说明。
- **DNA template**：main agent 生成图文或委托 Content Producer 制作视频时使用的输入模板。

## 存储结构

```text
xhs/dna/{dna-id}/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

原始笔记文本可临时放在 `xhs/ref/{dna-id}/notes/`；生成后的 report 必须进入目标 DNA 的 `reports/` 目录。

## 样本文件约定

```text
# 笔记标题（首个一级标题行，≤20 字）
正文第 1-2 行（开头）
正文主体段落……

#话题1 #话题2 #话题3
```

- 首个 `# ` 一级标题行识别为标题，其余内容为正文。
- 正文保持纯文本，不使用 markdown 小标题。
- 话题标签保持内联 `#话题` 形式。

## 职责边界

- 单篇样本只提供候选信号；账号比例、发布节奏、高数据共性、搜索意图地图必须由多样本或账号级数据聚合。
- 搜索关键词必须尽量落到用户可能提问；不能只写平台标签。
- 统计只做证据底座，不评分、不替代定性判断。
- 视觉语言有图片证据时才由视觉模型分析；缺失写「未观测」。
- 口播文案 DNA 独立聚合；样本不足时保持未启用。
- 不输出合规结论、账号权重或风格评分。

## Report - 单篇提取

```bash
xhs-style-profiler report \
  --input path/to/note.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://www.xiaohongshu.com/explore/..." \
  --output-dir xhs/dna/{dna-id}/reports
```

- `--cover-image`：封面本地图片，用于视觉证据。
- `--source-url`：原笔记链接；本地素材无链接时省略。
- `--weight`：样本权重，默认 1。
- `--focus`：限制该样本只影响指定维度，可重复传入。

Agent 生成 scaffold 后必须：

1. 补齐「样本与账号观测」：样本类型、账号与简介、发布时间、内容形式、数据线索、搜索关键词与用户可能提问、视频形态与授权信息。
2. 回读笔记原文，补齐 14 维的单篇结论、原文证据和可复用信号。
3. 单篇样本无法观测账号简介、图文/视频比例、发布节奏时写「未观测」。
4. 高数据样本必须回读创意、关键词与内容形式，不得只凭阅读量下结论。

## Build - 聚合 DNA 文档与模板

```bash
xhs-style-profiler build --dna-id {dna-id}
```

默认读取 `xhs/dna/{dna-id}/reports/`，输出：

```text
xhs/dna/{dna-id}/{dna-id}.dna.md
xhs/dna/{dna-id}/{dna-id}.template.md
```

也可显式传入 report 文件/目录：

```bash
xhs-style-profiler build \
  --input path/to/reports \
  --dna-id {dna-id}
```

Agent 聚合时必须：

1. 读取全部 DNA report，不能只看统计表。
2. 按 `weight` 与 `focus` 判断影响范围。
3. 区分高频共性、高权重偏好、局部借鉴、孤例和例外。
4. 标注样本覆盖度；单篇/少量样本不得称为稳定账号 DNA。
5. 聚合「关键词 → 用户问题 → 内容形式」的搜索意图地图。
6. 为每个维度写聚合结论、报告依据和可执行规则。
7. 确保 DNA 文档能完整推导 template。

## DNA Template

Template 是 main agent 的图文生产输入 / 视频制作 Brief 模板，不是成片制作模板。固定语义段：

1. 定位与核心传达
2. 选题与标题包装
3. 内容形式与发布节奏
4. 高数据创意模式
5. 互动与系列
6. 搜索意图与用户问题
7. 制作交接与 Pipeline
8. 口播文案 DNA（可选）

图文笔记由 main agent 直接生产；视频全案只输出 Brief。制作交接段必须写清 MainAgent 与 Content Producer 的交付物、Pipeline、素材授权和风格边界。Brief 未指定 Pipeline 时，Content Producer 可自由选择；指定 Pipeline 时必须直接采用。

## Update - 增量聚合

```bash
xhs-style-profiler update \
  --input xhs/dna/{dna-id}/reports/{new-sample}.report.md \
  --dna xhs/dna/{dna-id}/{dna-id}.dna.md \
  --template xhs/dna/{dna-id}/{dna-id}.template.md
```

脚本合并历史 report 与新 report，重新计算统计并保留 Agent 已完成内容。Agent 仍需重新审视聚合结论，并同步修订 DNA 文档和 template。

`--input` 可省略，用于只融合用户输入或另一个 DNA 的局部规则；此时必须传 `--user-input`。

## 用户输入转译

用户输入是参考信息，不是可直接入库的 DNA 规则。

```bash
--user-input "搜索流量优先，标题必须覆盖真实提问"
```

Agent 必须转译到具体维度，例如：

```text
search-intent-map：标题优先覆盖长尾提问，不只堆品类词
title-packaging：标题采用问题句式，并保留核心关键词
topic-portfolio：优先选择能承接搜索意图的教程/避坑选题
```

处理要求：

1. 在 DNA 文档的「用户输入转译区」记录 affected dimensions、DNA 修改和 template 修改。
2. 原话必须转译为可执行规则，不得直接抄进 template。
3. 与样本证据冲突时保留冲突说明，由用户选择优先级。

## Focus ID

| ID | 维度 |
|---|---|
| `positioning-core` | 定位与核心传达 |
| `topic-portfolio` | 选题组合 |
| `title-packaging` | 标题与包装 |
| `bio-profile` | 账号简介与主页表达 |
| `content-form-mix` | 内容形式与比例 |
| `publish-cadence` | 发布习惯 |
| `high-performer-patterns` | 高数据创意模式 |
| `visual-language` | 视觉语言 |
| `audio-language` | 声音语言 |
| `narration-dna` | 口播文案 DNA |
| `engagement-conversion` | 互动与转化 |
| `series-signature` | 系列与签名 |
| `search-intent-map` | 搜索意图地图 |
| `production-pipeline` | 制作管线倾向 |

## 统计与分词

脚本统计标题字数、句段、行数、标点、人称、emoji、话题标签等指标；中文高频信号使用相邻二字组合，仅作为候选线索。Agent 必须回读原文确认口头禅或签名式表达。分词结果不能直接作为 DNA 结论。

## 参考资料

- `references/account-dna-framework.md`（小红书账号级 DNA 框架 v1、搜索意图地图、Pipeline 映射与聚合边界）
