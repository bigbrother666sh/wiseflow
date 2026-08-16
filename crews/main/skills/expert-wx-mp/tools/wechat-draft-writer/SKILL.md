---
name: wechat-draft-writer
description: 依据内容 DNA instruction 和结构大纲撰写公众号初稿，并在产出后执行可观测 DNA 自评。
---

# wechat-draft-writer

> 本文是 `expert-wx-mp` 专家包内的工具说明书，由 Workflow 指引调用。

## 用途

把大纲和内容 DNA instruction 转化为风格一致、结构完整的初稿。

## 输入

1. 文章大纲（必填，通常来自 `wechat-topic-outline-planner`）
2. DNA instruction（必填，路径为 `dna/wx_mp/<dna-id>.md`）
3. 对应 evaluation（必填，路径为 `dna/wx_mp/<dna-id>.evaluation.md`）
4. 目标字数（可选，默认 1500-2500）
5. 补充素材（可选）

没有账号 DNA 时，先向用户确认是否使用 `dna/wx_mp/default-business.md`。

## 写前执行

1. 逐条读取 DNA「使用时必须执行」。
2. 将 14 维执行区转成本次大纲的段落、开头、论证、收束和标题策略。
3. 保留签名表达的使用条件，不机械堆砌高频词。
4. 排版主题不参与 DNA 执行。

## 写后自评

统计型 DNA：

```bash
wechat-style-profiler evaluate \
  --metrics dna/wx_mp/<dna-id>.metrics.json \
  --article output_articles/<article>/article.md \
  --output output_articles/<article>/dna-evaluation.json
```

手写 DNA：按 `.evaluation.md` 的观测物逐项计算，保留证据和总分。

总分低于 80 时先修订再交付。评估只说明 DNA 相似度，不替代事实核查、合规审核或内容质量打分。

## 输出契约

1. `初稿正文`
2. `字数统计`
3. `DNA evaluation 路径与总分`
4. `低分维度与修订说明`
5. `需人工确认的位置`

## 质量红线

- 不允许跳过 DNA instruction。
- 不允许跳过 DNA evaluation。
- 不允许把排版变化当作 DNA 符合证据。
- 不允许结构与大纲不一致。
- 不允许无证据改写事实或夸大承诺。

## 在 SOP 中的位置

- 上游：`wechat-topic-outline-planner`、`wechat-style-profiler`
- 下游：`wechat-title-generator`、`generate-wenyan-theme`
