---
name: wechat-style-profiler
description: 从多篇公众号文章统计跨篇共性，生成内容生产 instruction、可观测评估方案和机器评估指标。
---

# wechat-style-profiler

## 职责边界

本工具只建模内容与表达 DNA：
- 输入：至少 3 篇 `.md` / `.txt` 正文样本；`.docx` 先由 agent 提取为文本。
- 输出：`instruction`、`evaluation.md`、`metrics.json` 三件套。
- 不输出：排版主题、平台封禁词结论、合规判定或账号权重。

排版由 `generate-wenyan-theme` 独立处理。合规由发布前检查处理。这里不移植海外平台的英文违禁词规则；样本中出现的高风险表达只进入风险评估素材，不构成风格禁区。

## Build

```bash
wechat-style-profiler build \
  --input-dir wx_mp_ref/{公众号名}/articles \
  --dna-id {dna-id} \
  --author {公众号名} \
  --output-dir dna/wx_mp
```

输出：
- `dna/wx_mp/{dna-id}.md`
- `dna/wx_mp/{dna-id}.evaluation.md`
- `dna/wx_mp/{dna-id}.metrics.json`

## Evaluate

```bash
wechat-style-profiler evaluate \
  --metrics dna/wx_mp/{dna-id}.metrics.json \
  --article output_articles/{article}/article.md \
  --output output_articles/{article}/dna-evaluation.json
```

通过线为 80 分。未通过时先根据逐维度差异修订稿件，再重新计算。

## 统计规则

- 以单篇文章为统计单元，先算每篇指标，再取跨篇中位数和 MAD。
- 定性特征必须出现在至少 60% 样本中；孤例进入例外区。
- 高频表达按“出现在多少篇文章”计算 document frequency，不按单篇重复次数放大。
- 样本 3-4 篇为 low，5-9 篇为 medium，10 篇以上为 high。
- 当前不按阅读、点赞、在看加权：对标公众号拿不到这些字段。

## Agent 补齐要求

脚本是统计底座，不是最终风格判断。Build 后必须：
1. 读取样本和 `metrics.json`。
2. 按 `references/style-14d-framework.md` 建立「特征 × 文章」证据矩阵。
3. 将每个维度改写成可执行指令，填入 `{dna-id}.md` 的 14 维执行区。
4. 保留低置信度和例外，不用单篇特征覆盖共性。
5. 按 `references/calibration-checklist.md` 让用户确认后登记 INDEX。

## 参考资料

- `references/style-14d-framework.md`
- `references/style-dna-default-template.md`
- `references/style-profile-template.md`
- `references/style-dna-rules.md`
