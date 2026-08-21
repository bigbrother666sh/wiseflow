---
name: content-calibrator
description: DNA 表现评估引擎——消费 published-track 的发布与互动数据，按量触发（每平台每 DNA 累积 ≥5 条成熟记录）评估 DNA 好坏，趋势优先归因（账号基线归一化 + 漏斗映射 template 七部分），产出评估报告与优化建议，经用户确认后回写 DNA。发布记录与数据采集由 published-track 统一管理。
metadata:
  openclaw:
    emoji: 🎯
    requires:
      bins:
      - bash
      - sqlite3
      - python3
---

# Content Calibrator — DNA 表现评估引擎

> **四条评估铁律**：
> 1. **趋势优先**：绝对值只作上下文。数据好坏看「同账号相对值 + 其走向」——新号数据天然低、老号天然高，同 DNA 跨账号不可直接比绝对值，要的是趋势
> 2. **脚本只给证据**：聚合、基线、比值、走向由 `dna-eval.sh` 计算；好坏归因由 Agent 回读 DNA 文档与作品原文完成，脚本不下结论
> 3. **先排混杂再归因**：账号成熟度、粉丝自然增长、选题热度、季节性流量都会污染信号；排除不了的混杂，结论降级写「观察」不写「结论」
> 4. **DNA 更新必须用户逐条确认**：评估只产出建议，Agent 不得自动改 DNA

---

## 职责边界（与 review / published-track 的分工）

| 角色 | 回答什么 | 产出 |
|------|---------|------|
| `published-track` | 数据在哪 | 发布记录 + 互动指标（每日采集入库） |
| **本技能** | **这个 DNA 好不好、该怎么改** | `dna/<platform>/<dna-id>/evals/*.eval.md` 评估报告 + DNA 更新建议 |
| 各平台专家包 `review` workflow | 数据怎么了、为什么（按需） | 单篇诊断、周期复盘行动项（读本技能评估报告作素材，不重复计算） |

本技能的结论**必须落到 DNA 动作**（保持 / 调整某维度规则 / 调整 template 某部分），经用户逐条确认后走对应平台的 style-dna workflow 更新。单篇诊断、对标分析、业务行动项不属于本技能。

---

## 核心闭环

```
📥 每日数据采集(published-track) → 📊 阈值检查(--check) → 🧬 DNA 评估(聚合+归因) → 📝 评估报告 → 👤 用户逐条确认 → 🔁 style-dna 更新 DNA
```

### 触发机制：数据采集每天跑，评估按量触发

- **每日**：heartbeat 采集互动数据入库（published-track 职责，不变）。
- **按量**：每个（平台, DNA）的**成熟待评估记录**累积 **≥5 条**时评估一轮。成熟 = 发布 ≥3 天（数据稳定）；待评估 = `perf_evaluated=0` 且 `dna_id` 非空。一轮评估覆盖该 DNA 全部待评估记录（可多于 5 条）。
- **手动兜底**：低频 DNA 凑不满 5 条时，用户说「复盘一下这个 DNA」→ `--force` 强制评估。
- `dna_id=NULL`（历史补录/未归属）不参与 DNA 评估。

### 归因方法：漏斗 → template 七部分 → 17 维

互动漏斗各段映射 DNA template 的对应部分（wx_mp 维度示例，其他平台按各自 DNA 维度映射）：

| 漏斗卡点 | 先怀疑的 template 部分 | 可回溯的 DNA 维度（wx_mp 示例） |
|---------|----------------------|-------------------------------|
| 打开率低 | 选题、标题 | 选题角度、标题特征、封面图 |
| 完读率低 | 起、承、转 | 句式节奏、段落结构、起承转合微操、节奏感 |
| 收藏低 | 承、合（实用价值） | 论证逻辑、专业度体现 |
| 评论低 | 情感触点、互动设计 | 情感表达、修辞手法、签名式标记 |
| 关注/转化低 | 合、CTA | 语气与基调、思维特征 |

归因步骤：

1. 读 `dna-eval.sh` 聚合 JSON：每篇绝对值 + 同账号比值 + 每指标趋势走向。
2. `baseline_insufficient` 的记录只作绝对观察，不参与趋势结论。
3. 对照 `calibration/<platform>/.platform-state.json`、`audience.md` 排除账号阶段与受众因素。
4. 回读该 DNA 的 `{dna-id}.dna.md` / `{dna-id}.template.md` 与待评估作品原文（`source_folder`），把趋势变化落到具体 template 部分与维度。
5. 混杂排不掉 → 写「观察」；能归因 → 写「结论 + 建议」，每条建议注明改哪个维度 / template 部分。

---

## 评估产物

评估报告写入 Workspace：

```text
dna/<platform>/<dna-id>/evals/{YYYY-MM-DD}.eval.md
```

报告结构：

1. **整体判定**：这个 DNA 近期表现（趋势语言：改善 / 平稳 / 下滑），置信度与样本量。
2. **趋势表**：每指标的比值走势（引 `dna-eval.sh` 输出，不重算）。
3. **七部分归因**：哪个 template 部分在起作用 / 拖后腿，证据是哪几篇。
4. **逐条优化建议**：每条 = 建议内容 + 目标维度/template 部分 + 证据篇目。供用户逐条确认。
5. **观察区**：归因不了但值得记录的信号（含混杂说明）。

写完报告后必须调 `--mark-evaluated` 标记覆盖的记录，防止下轮重复评估。

---

## 脚本

### dna-eval.sh — 聚合引擎（唯一数据入口）

```bash
# 廉价阈值检查（heartbeat 每日跑，无触发不消耗后续 token）
./skills/content-calibrator/scripts/dna-eval.sh --platform wx_mp --check

# 聚合触发 DNA 的证据（绝对值 + 账号基线比值 + 趋势走向）
./skills/content-calibrator/scripts/dna-eval.sh --platform wx_mp

# 手动触发低频 DNA（不达阈值也评估）
./skills/content-calibrator/scripts/dna-eval.sh --platform wx_mp --dna-id dna-0 --force

# 评估报告写完后标记（防重复评估）
./skills/content-calibrator/scripts/dna-eval.sh --platform wx_mp --mark-evaluated --ids 3,4,5
```

参数：`--min-samples 5`（触发阈值）、`--mature-days 3`（成熟窗口）、`--baseline-window 10`（账号基线取此前最多 N 篇均值）。须从 Workspace 根调用。

基线语义：同账号**此前**（发布日更早）最多 N 篇的指标均值，避免后视；此前 <3 篇 → `baseline_insufficient`。`account` 为空的记录归入未知账号组，不与其他账号混算。

### query-metrics.sh — 单篇指标查询

```bash
./skills/content-calibrator/scripts/query-metrics.sh --platform wx_mp --source-folder "output_articles/xxx"
```

### init.sh — 平台初始化

```bash
./skills/content-calibrator/scripts/init.sh --platform <platform_id>
```

幂等。创建 `calibration/<platform>/`（`.platform-state.json` baseline 兜底参考 + `audience.md` + `benchmark.md`）。

---

## Heartbeat 集成（凌晨任务）

1. 数据采集：按 published-track 流程全量更新（每日必跑）。
2. 阈值检查：各启用平台跑 `dna-eval.sh --check`；全部 `triggered=false` → 本轮评估结束。
3. 有触发 → 对每个触发 DNA：跑聚合 → 按归因方法分析 → 写 `evals/{date}.eval.md` → `--mark-evaluated`。
4. 汇总：上报本轮评估的 DNA、整体判定与待用户确认的优化建议。**Agent 不得自动更新 DNA。**

派发纪律：heartbeat isolated 会话中全部流程须**主 agent inline 执行**，不 spawn subagent、不 sessions_yield（评估需连续回读多文件，隔离会话无上下文污染问题）。

---

## Status — 状态看板

向用户报告校准状态时展示：

```
🧬 Content Calibrator 状态（DNA 表现评估）

【平台】wx_mp：baseline 未定 / 已定
【待评估】dna-0：3/5 条成熟记录（未触发）
【最近评估】dna/wx_mp/dna-0/evals/2026-08-18.eval.md — 判定：改善
【待确认建议】2 条
```

数据来源：`dna-eval.sh --check` + `dna/<platform>/*/evals/` 目录。

---

## 历史说明

本技能前身为「内容校准预测循环」（统一 rubric 打分 + 盲预测 + 阈值门 + bump 升级）。2026-08-20 起 rubric 体系废除：发布前不再打分，判断准则不再是独立进化对象，发布数据直接关联 DNA（`pub_*` 表 `dna_id` 列）做表现评估。DB 中 `cal_*` 列为历史兼容保留。
