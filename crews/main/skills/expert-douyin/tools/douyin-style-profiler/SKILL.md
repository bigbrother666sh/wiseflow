---
name: douyin-style-profiler
description: 提取抖音账号级 DNA：单条视频生成 report，按 DNA ID 聚合定位、选题、标题、内容形式、发布节奏、高数据创意与制作管线，推导 main agent 的 Brief template。
metadata:
  openclaw:
    emoji: 🧬
---

# douyin-style-profiler

抖音账号级 DNA 提取与聚合工具。输入是**视频转录文本**（口播全文 + 标题/描述/时长/互动线索，由 Agent 先整理成 `.md` / `.txt`）与可选封面 / 首帧图；不接受视频文件或链接作为直接输入。

DNA 的用途是指导 main agent 选题、包装、账号表达和视频制作 Brief；不指导 main agent 直接产出全片。

## 产物模型

```text
单条视频 -> DNA report
同一 DNA 下的全部 report + 权重/focus + 用户输入 -> DNA 文档
DNA 文档 -> main agent Brief template
```

- **DNA report**：单条样本的账号级观测与 13 维提取结果。
- **DNA 文档**：聚合后的账号级规则与样本覆盖度说明。
- **DNA template**：main agent 生成内容或委托 Content Producer 时使用的 Brief / 生产输入模板。

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

原始转录文本可临时放在 `douyin/ref/{dna-id}/transcripts/`；生成后的 report 必须进入目标 DNA 的 `reports/` 目录。

## 职责边界

- 单条样本只提供候选信号；账号比例、发布节奏、高数据共性必须由多样本或账号级数据聚合。
- 统计只做证据底座，不评分、不替代定性判断。
- 视觉语言有图片/关键帧证据时才由视觉模型分析；缺失写「未观测」。
- 口播文案 DNA 独立聚合；样本不足时保持未启用。
- 不输出合规结论、账号权重或风格评分。

## Report - 单条提取

```bash
douyin-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/cover.jpg \
  --source-url "https://www.douyin.com/video/..." \
  --duration 89 \
  --output-dir douyin/dna/{dna-id}/reports
```

- `--cover-image`：封面或首帧本地图片，用于视觉证据。
- `--source-url`：原视频链接；本地素材无链接时省略。
- `--duration`：视频时长（秒），用于口播密度统计。
- `--weight`：样本权重，默认 1。
- `--focus`：限制该样本只影响指定维度，可重复传入。

Agent 生成 scaffold 后必须：

1. 补齐「样本与账号观测」：样本类型、账号与简介、发布时间、内容形式、数据线索、视频形态与授权信息。
2. 回读转录原文，补齐 13 维的单条结论、原文证据和可复用信号。
3. 对账号简介、内容比例、发布节奏等账号级字段，单条样本无法观测时写「未观测」。
4. 高数据样本必须回读创意与内容形式，不得只凭播放量下结论。

## Build - 聚合 DNA 文档与模板

```bash
douyin-style-profiler build --dna-id {dna-id}
```

默认读取 `douyin/dna/{dna-id}/reports/`，输出：

```text
douyin/dna/{dna-id}/{dna-id}.dna.md
douyin/dna/{dna-id}/{dna-id}.template.md
```

也可显式传入 report 文件/目录：

```bash
douyin-style-profiler build \
  --input path/to/reports \
  --dna-id {dna-id}
```

Agent 聚合时必须：

1. 读取全部 DNA report，不能只看统计表。
2. 按 `weight` 与 `focus` 判断影响范围。
3. 区分高频共性、高权重偏好、局部借鉴、孤例和例外。
4. 标注样本覆盖度；单条/少量样本不得称为稳定账号 DNA。
5. 为每个维度写聚合结论、报告依据和可执行规则。
6. 确保 DNA 文档能完整推导 template。

## DNA Template

Template 是 main agent 的 Brief / 内容生产输入模板，不是成片制作模板。固定语义段：

1. 定位与核心传达
2. 选题与标题包装
3. 内容形式与发布节奏
4. 高数据创意模式
5. 互动与系列
6. 制作交接与 Pipeline
7. 口播文案 DNA（可选）

制作交接段必须写清 MainAgent 与 Content Producer 的交付物、Pipeline、素材授权和风格边界。Brief 未指定 Pipeline 时，Content Producer 可自由选择；指定 Pipeline 时必须直接采用。

## Update - 增量聚合

```bash
douyin-style-profiler update \
  --input douyin/dna/{dna-id}/reports/{new-sample}.report.md \
  --dna douyin/dna/{dna-id}/{dna-id}.dna.md \
  --template douyin/dna/{dna-id}/{dna-id}.template.md
```

脚本合并历史 report 与新 report，重新计算统计并保留 Agent 已完成内容。Agent 仍需重新审视聚合结论，并同步修订 DNA 文档和 template。

`--input` 可省略，用于只融合用户输入或另一个 DNA 的局部规则；此时必须传 `--user-input`。

## 用户输入转译

用户输入是参考信息，不是可直接入库的 DNA 规则。

```bash
--user-input "账号更偏实拍拼接，少用纯动画"
```

Agent 必须转译到具体维度，例如：

```text
content-form-mix：主形态为实拍拼接，纯动画仅作补充
production-pipeline：Brief 默认使用 video-producer:default（montage）
visual-language：画面保持实拍质感，不采用插画化风格
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
| `production-pipeline` | 制作管线倾向 |

## 统计与分词

脚本统计转录文本的句段、标点、人称、口播密度等指标；中文高频信号使用相邻二字组合，仅作为候选线索。Agent 必须回读原文确认口头禅或签名式表达。分词结果不能直接作为 DNA 结论。

## 参考资料

- `references/account-dna-framework.md`（抖音账号级 DNA 框架 v1、Pipeline 映射与聚合边界）
