---
name: wechat-title-generator
description: 公众号标题生成与打分。生成 8 个不同力度的候选标题，筛除低质标题，逐项打分并推荐最优解 + 稳妥版 + 传播版。
---

# wechat-title-generator — 工具说明

> 本文是 `expert-wx-mp` 专家包内的工具说明书，不独立出现在技能列表中。由相关 Workflow 指引调用。

## 用途
稳定产出高点击意愿、不过度标题党、符合公众号语境的标题，并明确推荐最优解。

## 输入
1. 已确认的选题和大纲（来自 `wechat-topic-outline-planner`）
2. 目标读者
3. 文章目标
4. 文风 DNA（来自 `wechat-style-profiler`）
5. 可选的风险边界

## 工作流
1. 先提炼文章承诺、情绪点、反差点和读者收益。
2. 使用 `references/title-rubric.md` 生成 8 个标题，覆盖不同力度层级。
3. 筛除违反硬约束的标题。
4. 对保留标题逐项评分，并推荐 1 个最佳标题。
5. 同时给出 1 个更稳妥版本和 1 个更强传播版本。

## 输出契约
按以下顺序输出：
1. `Title Strategy`
2. `Title Candidates x8`
3. `Best Title Recommendation`
4. `Safer Alternative`
5. `Stronger Alternative`
6. `Eliminated Titles And Why`

## 硬约束
- 必须生成恰好 8 个标题。
- 标题不能出现引号。
- 标题不能出现冒号。
- 标题不能出现破折号。
- 标题中如果出现两个或以上分句，分句之间必须使用逗号。
- 标题要有情绪或反差。
- 可以适度夸张，允许使用高情绪表达，比如"这是我读过最好的一篇文章""我看到了新世界的大门""我被震到了"这一类强感受句式。
- 如果正文内容是人物故事，则标题必须根据主人公人设和背景提炼,便于引发读者代入和共鸣,如:
  > 数字型:「新号一周收入1000,全靠这7步」
  > 反差型:「35岁才觉醒,比20岁更值钱」
  > 痛点型:「写公众号没人看?你可能第一步就错了」

## 边界
- 不写大纲，不写正文。
- 如果主题还没定，先交给 `wechat-topic-outline-planner`。

## 在 SOP 中的位置
- 上游：`wechat-topic-outline-planner`（大纲）、`wechat-draft-writer`（初稿）、`wechat-style-profiler`（文风 DNA）。
- 下游：定题后 → `wx-mp-publisher`（relay 发布到草稿箱）。

## 参考文件
- 标题评分：`references/title-rubric.md`
