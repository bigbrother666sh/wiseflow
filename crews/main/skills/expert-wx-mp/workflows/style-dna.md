# 公众号内容 DNA 生产与使用 Workflow

DNA 只描述内容、标题和表达策略。排版由 `wenyan-theme` 独立管理，不参与 DNA 采样、组合或评分。

## 入口判断

走本 Workflow：
- “给这个号建 DNA / 风格模型”
- “按照这个号的内容风格写”
- “提炼这几篇文章的共同风格”
- “换一种内容风格”

不走本 Workflow：
- “照着这篇排版” -> 直接走 `generate-wenyan-theme`
- “只换颜色 / 字体 / 间距” -> 直接更新 `wenyan-theme/index.json`

## 统一存储

- DNA：Workspace 根 `dna/wx_mp/`
- 样本：`wx_mp_ref/{公众号名}/articles/`
- 证据矩阵：`wx_mp_ref/{公众号名}/evidence-matrix.md`
- 样本清单：`wx_mp_ref/{公众号名}/sample-inventory.md`
- 排版主题：`wenyan-theme/` + `wenyan-theme/index.json`

专家包内的 `tools/wechat-style-profiler/references/` 只是模板和方法论，不是运行时 DNA 存储。

## 方式一：从账号历史文章统计

用户给公众号名且 `wx-mp-hunter` 可用时：

1. 拉取最近 30 篇可获取文章；不足 30 篇取全部，不按阅读、点赞、在看筛选，因为对标账号拿不到这些数据。
2. 正文保存到 `wx_mp_ref/{公众号名}/articles/`，剔除重复、删除、付费或正文缺失样本。
3. 建立 `sample-inventory.md`，记录标题、发布时间、主题、篇幅、开头、结构、结尾、高表达和例外。
4. 运行统计工具：

```bash
wechat-style-profiler build \
  --input-dir wx_mp_ref/{公众号名}/articles \
  --dna-id {dna-id} \
  --author {公众号名} \
  --output-dir dna/wx_mp
```

5. 读取 `dna/wx_mp/{dna-id}.metrics.json` 和原文，按 14 维框架补 `evidence-matrix.md`。
6. 把矩阵结论改写成 `{dna-id}.md` 的直接执行指令；60% 以下覆盖率的特征只进例外区。
7. 请用户按校准清单确认；确认后登记 `dna/wx_mp/INDEX.md`。

## 方式二：用户提供样本

1. 样本少于 3 篇：不生成统计 DNA，说明证据不足；可临时手写低置信 instruction，但不能登记为长期资产。
2. 3-4 篇：可以生成，标记 low confidence。
3. 5-9 篇：可以生成，标记 medium confidence。
4. 10 篇以上：可以生成，标记 high confidence。
5. 把文本文件集中到 `wx_mp_ref/{公众号名}/articles/` 后运行方式一的 build 命令。

## 方式三：使用现成 DNA

1. 读取 `dna/wx_mp/INDEX.md` 选择主 DNA。
2. 可叠加 0-2 个辅助 DNA；冲突按 INDEX 优先级处理。
3. 生产前必须读取主 DNA 的「使用时必须执行」。
4. 生成后必须执行对应 `.evaluation.md`。
5. 没有账号 DNA 时，经用户确认后用 `default-business.md` 兜底。

## 生产交付契约

统计型 DNA 必须同时交付：

1. **Instruction**：`dna/wx_mp/{dna-id}.md`，写稿前读取，内容是直接执行规则。
2. **Evaluation**：`dna/wx_mp/{dna-id}.evaluation.md`，写完后按观测物和公式自评。
3. **Metrics**：`dna/wx_mp/{dna-id}.metrics.json`，供命令计算，不依赖主观感觉。

手写默认 DNA 可没有 metrics，但 evaluation 必须仍含观测物、分值和通过线。

## 使用 DNA 生产内容

每次内容生产执行两阶段：

1. **写前**：读取 instruction；排版主题选择不得影响 DNA 判断。
2. **写后**：统计型 DNA 运行：

```bash
wechat-style-profiler evaluate \
  --metrics dna/wx_mp/{dna-id}.metrics.json \
  --article output_articles/{article}/article.md \
  --output output_articles/{article}/dna-evaluation.json
```

总分低于 80、任一关键维度为 0、或用户明确指出风格偏差时，先修订再重新计算。手写 DNA 按对应 evaluation 表逐项打分。

## 统计原则

- 单篇文章先算指标，跨篇取中位数和 MAD。
- 定性特征按文章覆盖率判断，不按单篇重复次数放大。
- 不使用互动数据加权。
- 不把排版 HTML、编辑器模板或视觉主题当作内容 DNA。
- 样本统计描述“像不像”，不替代事实核查和合规审核。
