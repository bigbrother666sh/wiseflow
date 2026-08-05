---
name: content-calibrator
description: 内容校准预测循环——打分+盲预测合一 → 发布 → 记录 → T+3d 复盘 → 进化 rubric。本技能负责打分+预测（blind sub-agent + score-only.sh + commit-prediction.sh + 阈值门）与校准闭环；发布记录与数据采集由 published-track 统一管理。
metadata:
  openclaw:
    emoji: 🎯
    requires:
      bins:
      - bash
      - sqlite3
      - node
---

# Content Calibrator — 内容校准预测循环

> **三条不可妥协原则**：
> 1. **盲预测**：预测必须在看到实际数据之前写完，写完即 immutable
> 2. **升级需盲重打验证**：新公式必须盲重打 10 篇 + `validate-rubric.sh` 降幅达标才落地，Agent 不得自动升级
> 3. **rubric 是工作台不是博物馆**：被推翻/吸收的观察删掉，git history 是档案

---

## 核心设计：per-work 归集 + 统一 rubric

**一个作品 = 一个打分 + 一个预测 + 一个复盘。** 作品的内在内容质量与发布平台无关，故打分/预测/复盘按作品归集，rubric 全平台统一，**放行阈值也全局统一**（质量门是作品本身的事，不分平台）。平台差异（baseline 量级、受众、对标账号）仅作为**预测的输入数据**按平台保留。

| 组件 | 归集方式 | 位置 |
|------|---------|------|
| rubric 公式 | **统一** | `calibration/rubric_notes.md` |
| rubric 观察 memo | **统一** | `calibration/rubric-memo.md` |
| rubric 循环状态（mode/samples/rubric_version/**threshold**） | **统一** | `calibration/.cheat-state.json` |
| 打分（7 维 + composite） | **per-work** | `<work>/calibration/score.json` |
| 预测 | **per-work** | `<work>/calibration/prediction.md` |
| 复盘（含多平台分析） | **per-work** | `<work>/calibration/retro.md` |
| baseline / audience / benchmark | **per-platform** | `calibration/<platform>/.platform-state.json` + `audience.md` + `benchmark.md` |
| 发布记录 + 互动指标 | **per-platform** | published-track DB（`pub_<platform>` 表） |

> `<work>` 即作品目录：文章为 `output_articles/<article-english-title>/`，视频为 `output_videos/<topic-en-slug>/`。

---

## 核心闭环

```
📊 打分+盲预测 → 🚀 发布 → 📝 记录(1B) → 📈 T+3d 复盘 → 🧬 进化 rubric
                                    │
                                    ├─ 3a: 单篇复盘批量（retro.md + rubric-memo.md）
                                    └─ 3b: 综合评估（detect-bump-signals.sh + 混杂因素 + 建议）
```

打分与盲预测**同一次出分**内完成（合并理由：已读稿件、已出分值，顺手出预测；
复盘拆两步：先批量写完所有单篇 retro.md + 观察进 rubric-memo.md（3a），再做跨作品综合评估（3b）——综合评估需本批全部观察落盘后才有效。

### 派发策略：blind sub-agent 是条件派发，不是强制

blind sub-agent 的隔离价值在于"主对话已看过用户对话/实绩/复盘历史，inline 打分会污染"。**这一前提只在交互式会话成立。** 发布常走定时任务 + isolatedSession，此时主 agent 本就是全新对话、无上下文，再套一层隔离 subagent 买不到隔离收益，反而 subagent 经 `sessions_yield` 回包会让 isolated 主 agent 误判本轮结束、截断后续发布动作（见 gotcha：心跳 isolated session 交互死锁）。

| 会话场景 | 打分方式 | 理由 |
|---------|---------|------|
| **交互式会话**（主 agent 有对话/复盘上下文） | `sessions_spawn` blind sub-agent | 主对话被污染，需 spawn 硬隔离 |
| **定时 / isolatedSession**（发布 cron、heartbeat 触发） | **主 agent inline 打分**，不派 subagent | 全新对话无上下文，盲条件由"发布前=无实际数据"天然满足；避免 sessions_yield 截断发布流 |

**inline 打分时必须遵守的隔离纪律**（用文字约束替代 spawn 硬隔离，弱一档但可接受）：打分前**只读**稿件 + `calibration/rubric_notes.md`；**不要读** `rubric-memo.md`、`.cheat-state.json`、其他 work 的 `calibration/`、`audience.md`、`benchmark.md`。读完即出分 + 预测，不翻历史。

---

## 与 published-track 的集成

发布流程为 **打分+预测(1A) → 发布 → 记录(1B)**。**打分+预测（1A）由本技能负责，发布记录（1B）由 published-track 负责。**

### 流程 1A·打分+盲预测（发布前自检）

发布前对稿件做盲打分 + 盲预测 + 阈值门，**避免自创自评**。派发方式按上方"派发策略"表，依会话场景选 inline 或 blind sub-agent。

1. **出分+出预测**（inline 或 blind sub-agent 二选一，见派发策略表）：
   - **交互式会话**：主 agent `sessions_spawn` 一个 blind sub-agent，只喂 `script_path`（稿件/视频定稿）+ `calibration/rubric_notes.md`。sub-agent 硬禁读 `.cheat-state.json`/各 work 的 `calibration/`/`rubric-memo.md`/`audience.md`/`benchmark.md`/对话历史。
   - **定时 / isolatedSession**：主 agent 自己 inline 打分，只读稿件 + `calibration/rubric_notes.md`，不读上述禁读文件，不翻对话历史。
   - 两种方式输出同一份严格 JSON：
   - 7 维分（ER/HP/SR/QL/NA/AB/PV，各 0-5）+ per-dim confidence
   - **盲预测草稿**：cold-start 期（前 5 个作品）= 一句话 bet；过 cold-start = 每目标平台的 bucket + 概率分布 + 中枢 + 反事实场景 + 关键校准假设
2. 主 agent 拿分调 `score-only.sh` 校验 + 算 composite + 判阈值门：
   ```bash
   ./skills/content-calibrator/scripts/score-only.sh \
     --content-path "output_articles/xxx/article.md" \
     --cal-er 3 --cal-hp 4 --cal-sr 3 --cal-ql 4 --cal-na 3 --cal-ab 4 --cal-pv 2
   ```
   返回 JSON 含 `passed` 与 `failing_dims`。阈值取自根级 `calibration/.cheat-state.json` 的 `score_threshold`（**全局**，默认 0=不拦截），**每维需 > 阈值**才算通过。`--platform` 可选，仅用于校验该平台是否启用 calibration。
3. 主 agent 调 `commit-prediction.sh` 把 **score + 预测**落盘到 `<work>/calibration/`：
   ```bash
   ./skills/content-calibrator/scripts/commit-prediction.sh \
     --work-dir "output_articles/xxx" --platform wx_mp \
     --cal-er 3 --cal-hp 4 --cal-sr 3 --cal-ql 4 --cal-na 3 --cal-ab 4 --cal-pv 2 \
     --prediction-file /tmp/prediction-draft.md
   ```
   写 `score.json` + `prediction.md`。**同 work 重复打分直接覆盖**（用户有意见/未过阈值 → 改稿重打，新结果覆盖旧的）。
4. **阈值门**：`passed=false` → 主 agent 据 `failing_dims` 改稿 → 按派发策略重新出分+预测 → 再判门。**最多 2 轮**，仍不达标 → 暂停发布、上报用户裁定。
5. `passed=true` → 放行，进入发布技能。
6. **平台未启用 calibration**（`calibration/<platform>/.platform-state.json` 不存在或 `enabled=false`）→ 跳过 1A，直接发布。

> **视频内容**：打分+预测对象是**脚本定稿**（storyboard/口播稿），不是成片。视频技能流程 = 打分+预测(定稿) → 制作 → 发布 → 记录。成片后不再打分。
>
> **多平台发布**：作品一次打分+预测，预测文件内含每个目标平台的 bucket/中枢（各平台 baseline 不同）。打分维度分只有一组。发布到 N 个平台 → `record.sh` 调 N 次，每次同一 `--source-folder`（指向 `<work>`），record.sh 自动从同一份 score.json 读分。

### 流程 1B·发布记录（由 published-track 承接）

打分通过并发布成功后，由 `published-track/scripts/record.sh` 落库。**record.sh 直接从 `<work>/calibration/score.json` 读分**（不再传 `--cal-*` 入参）：默认要求 score.json + prediction.md 齐全否则报错（拦截漏跑 1A）；`--no-cal` 显式跳过（补发/不打分）。详见 `published-track/SKILL.md`。

### 平台打分开关 + 全局阈值

`content-calibrator/scripts/cal-toggle.sh`：
- 平台开关：`--platform <p> --enable/--disable/--status`（per-platform）
- 全局阈值：`--threshold`（查看）/ `--set-threshold N`（设置，每维 0-5，需 >N 才放行；0=不拦截）/ `--list`（总览）

### 数据采集由 published-track 统一管理

**content-calibrator 不直接抓取平台数据**, 详见 `published-track`。

---

## 路由表（触发词 → 操作）

| 用户说 | 操作 | 前置条件 |
|--------|------|----------|
| "初始化校准 [--platform xxx]" | Init | 首次使用 |
| "打分这篇 [path] --platform xxx" / "打分+预测" | Score+Predict | rubric_notes.md 存在 |
| "复盘 [work] --platform xxx" / "T+3d 数据来了" | Retro (Step 3a 单篇 + 3b 综合评估) | 有预测 + 已发布 + 过时间窗口 |
| "升级公式" / "bump rubric" | Rubric 升级（用户发起） | 综合评估已完成 + 用户确认 |
| "导入对标 --platform xxx" / "learn from" | LearnFrom | 有 viral-chaser 报告或用户提供对标数据 |
| "校准状态 [--platform xxx]" / "calibration status" | Status | 任意时刻 |
| "加维度 XX" | 维度变更 | **必须用户确认** |
| "改权重 XX" | 权重变更 | **必须用户确认** |

> Predict 不再是独立路由项——它已合并进"打分"。如需单独重跑预测，用"打分这篇"即可（会覆盖 `prediction.md`）。

### 平台启用控制

**是否启用某个平台的 calibration，必须由用户决定。** Agent 不得自动启用。

- 启用：`./skills/content-calibrator/scripts/cal-toggle.sh --platform <platform> --enable`
- 停用：`./skills/content-calibrator/scripts/cal-toggle.sh --platform <platform> --disable`
- 查看状态：`./skills/content-calibrator/scripts/cal-toggle.sh --list`

Agent 在复盘或发布时，发现对应平台未启用 calibration，**不得自动启用**，应告知用户"该平台未启用 content-calibrator，如需启用请确认"。

`--platform` 为必填参数（Init 除外）。支持的平台 ID：

| 平台 ID | 平台 | 内容形态 |
|---------|------|---------|
| `wx_mp` | 微信公众号 | 长文 |
| `wx_channel` | 微信视频号 | 短视频 |
| `xhs` | 小红书 | 图文/视频笔记 |
| `zhihu` | 知乎 | 文章/回答 |
| `bilibili` | B站 | 视频 |
| `douyin` | 抖音 | 短视频 |
| `kuaishou` | 快手 | 短视频 |
| `toutiao` | 今日头条 | 文章 |
| `youtube` | YouTube | 视频 |

---

## 文件结构

```
<workspace>/
├── calibration/                     # 校准系统根目录
│   ├── rubric_notes.md              # 统一评分公式（blind sub-agent 可读）
│   ├── rubric-memo.md               # 统一观察记录（blind 不可读）
│   ├── .cheat-state.json            # 统一 rubric 循环状态（mode/samples/bump/score_threshold）
│   ├── wx_mp/                       # 平台专属*数据*（无 rubric、无 predictions、无 threshold）
│   │   ├── .platform-state.json     # baseline / enabled / content_form
│   │   ├── audience.md              # 受众画像
│   │   └── benchmark.md             # 对标账号
│   └── xhs/ ...
├── output_articles/<work>/
│   └── calibration/
│       ├── score.json               # 7 维 + composite + rubric_version + 时间戳（重打覆盖）
│       ├── prediction.md            # 盲预测（发布前重打覆盖；发布后 immutable）
│       └── retro.md                 # T+3d 写一次，多平台分析内含（immutable）
└── output_videos/<work>/
    └── calibration/                 # 同上
```

---

## Init — 初始化

为指定平台创建 `calibration/<platform>/` 目录和平台数据文件。**首次初始化时同时创建根级统一 rubric（若不存在）。**

**两种触发方式**：
- **用户主动**：用户说"初始化校准"或"我要做 XX 平台" → 交互式问答
- **Agent 不得自主初始化**：必须用户明确要求

### 用户主动触发流程

1. 询问或从 `--platform` 参数获取平台 ID
2. 若 `calibration/rubric_notes.md` 不存在 → 创建根级统一 rubric（v0）+ `.cheat-state.json`（cold-start）+ `rubric-memo.md`
3. 创建 `calibration/<platform>/` + `.platform-state.json` + `audience.md` + `benchmark.md`
4. 询问用户：内容形态、典型篇幅、发布频率、对标账号（可选）、该平台 baseline
5. 如有对标账号 → 触发 LearnFrom

```bash
./skills/content-calibrator/scripts/init.sh --platform <platform_id>
```

幂等——已存在则跳过。

---

## Score+Predict — 打分+盲预测（合并）

给单篇稿子打 rubric 分 + 出盲预测，在发布前作为自检门（流程见上方"流程 1A"）。**脚本不做 LLM 打分/预测**；打分+预测由主 agent 出（inline 或 blind sub-agent，按上方"派发策略"表选），脚本只做算术、门禁、落盘。

**隔离规则**（无论 inline 还是 subagent，白名单/禁读清单相同；区别只是 inline 靠文字自律、subagent 靠 spawn 硬隔离）：

- **白名单只读**：稿件（`script.md`/`article.md`/`post.md`）+ `calibration/rubric_notes.md`
- **rubric 路径**：统一 rubric 只在根级 `calibration/rubric_notes.md`。`calibration/<platform>/` 下**没有独立 rubric**，只有 `audience.md`/`benchmark.md`/`.platform-state.json`（平台目录里的 `rubric_notes.md` 是指向根级的软链，读它等于读根级）。派发 subagent 时应把根级 rubric 路径或内容显式喂给 subagent，不要让 subagent 自己去平台目录找。
- **硬禁读**：`rubric-memo.md`、`.cheat-state.json`、各 `<work>/calibration/`、`audience.md`、`benchmark.md`、对话历史
- **输出**：严格 JSON = 7 维分（各 0-5）+ per-dim confidence + 盲预测草稿
- 校准池重打分（Rubric 升级）**强制** blind sub-agent，不接受 inline fallback——升级是交互式深度操作，主 agent 必有上下文，且盲重打需要严格隔离保证验证有效

### 盲预测的"盲"与落盘分工

- **blind subagent 产盲预测本体**（bucket/probability/counterfactual/assumptions，或 cold-start 一句话 bet）——它没看 actuals/history/audience，预测是真正的"事前赌"
- **主 agent/脚本在落盘时追加锚点注释**（找历史相近 composite 的实绩作参考）——这是派生注释，不污染盲预测本体
- 落盘后 `prediction.md` 的预测段 immutable（发布后不得覆盖；发布前重打可覆盖）

### Cold-start 简化

前 5 个作品不要求完整 bucket 数字，只给 7 维分 + 一句话 bet。第 5 个作品复盘后解锁完整预测。计数在 `calibration/.cheat-state.json` 的 `calibration_samples`（全局）。

### 当前默认 rubric（v0）

7 个维度，每维 0-5 整数分：

| 维度 | 代号 | 含义 | 权重 |
|------|------|------|------|
| 情感共鸣 | ER | 读者能否产生"说的就是我"的代入感 | ×1.5 |
| 钩子强度 | HP | 标题/开头是否锁定注意力 | ×1.5 |
| 社会议题共振 | SR | 是否触及社会讨论 | ×1.5 |
| 金句密度 | QL | 是否有独立可传播的表达 | ×1.0 |
| 叙事性 | NA | 是否有清晰的故事弧线 | ×1.0 |
| 受众广度 | AB | 话题的普适程度 | ×1.0 |
| 实用价值 | PV | 读者能否获得可操作的信息 | ×1.0 |

**composite = (ER×1.5 + HP×1.5 + SR×1.5 + QL + NA + AB + PV) / 8.5 × 2.0**

---

## Retro — 复盘

复盘分两步：**先批量做完所有单篇复盘，再一次性检测 bump 信号**。不在单篇复盘中途插 bump 检测——bump 是跨作品统计判断，需要本批全部观察落盘后才有效。

### 两个入口

#### 入口 1：凌晨 HEARTBEAT 自动复盘

心跳巡检时：
- 调 `query-retro-pending.sh` 一键拿待复盘作品列表 + 互动数据
- 按 Step 3a → Step 3b 顺序执行（见下方流程）

#### 入口 2：用户导入对标

用户主动提供对标账号/爆款内容数据，触发 LearnFrom。这是**校准 rubric 本身**的入口——通过分析对标内容，提炼高流量内容的 pattern，调整 rubric 维度和权重。

> **复盘的本质**：复盘是"拿实际数据验证预测，提炼观察，可能触发 rubric 升级"。导入对标是"从外部信号校准 rubric 的初始假设"。两者互补：复盘是内源校准，对标是外源校准。

### Step 3a·单篇复盘（批量）

对 `query-retro-pending.sh` 返回的每个待复盘作品，**依次**执行：

1. 读 `prediction_path` 拿盲预测（路径已在 JSON 里，无需自己拼）
2. 对比预测 vs `platforms` 里各平台的实际 `metrics`（数据已在 JSON 里，无需再查 DB）
3. 写 `<source_folder>/calibration/retro.md`（T+3d 写一次，immutable，含多平台实绩对比 + 假设验证/推翻）
4. 提炼本篇观察 → 追加写入**统一** `calibration/rubric-memo.md`（根级，非平台目录）
5. 更新 `calibration/.cheat-state.json` 的 `calibration_samples`

**所有待复盘作品全部写完 retro.md + rubric-memo.md 后，才进入 Step 3b。** 不在单篇之间插 bump 检测。

### Step 3b·综合评估（一次性）

全部单篇复盘完成后，调脚本一次性检测偏差信号并做综合评估：

```bash
./skills/content-calibrator/scripts/detect-bump-signals.sh
```

**纯 DB 操作**，数据全部来自 `published_track.db`（`cal_score_*` 盲打分 + 互动指标实测），不扫文件系统。

脚本逻辑：
1. 查所有 `cal_enabled=1 AND cal_bump_evaluated=0` 的记录
2. 对每条：`cal_score_*` + 互动指标 → log 桶归一化到 0-5 `actual_score`（0→0, 1-10→1, 11-50→2, 51-200→3, 201-1000→4, 1000+→5）
3. **偏差检测**（per record = per work × platform）：维度分 ≥3 但 actual ≤2 = 高估；维度分 ≤2 但 actual ≥3 = 低估
4. 偏差信号写回该记录的 `cal_bias_signals` 列，`cal_bump_evaluated` 置 1
5. **聚合**：查所有 `cal_bias_signals IS NOT NULL` 的记录，按维度 + 方向统计 count，≥3 → bump 信号触发
6. **触发时自动清信号**：`recommend_bump=true` 时清空 `cal_bias_signals`（信号已达阈值被消费）；未触发时保留，跨轮累积直到达标

每条记录只处理一次（`cal_bump_evaluated` 标记）。未达阈值的信号保留在 DB 里，下一轮新记录的信号会叠加到聚合计数上，直到某维度+方向累计 ≥3 触发 bump。触发后清空，下轮从零开始。

返回 JSON：

```json
{
  "newly_processed": 20,
  "data_points": 112,
  "signals": [
    {"dimension": "pv", "direction": "overestimate", "count": 17, "threshold": 3, "triggered": true,
     "platforms": {"xhs": 13, "wx_mp": 1, "douyin": 1, "youtube": 1, "wx_channel": 1},
     "examples": [...]}
  ],
  "triggered_signals": [...],
  "recommend_bump": true
}
```

`platforms` 字段给出该信号的各平台分布，供 Agent 一眼判断混杂因素。

Agent 拿到后：
- `recommend_bump=false` → 本轮无系统性偏差，复盘结束
- `recommend_bump=true` → **混杂因素评估**（Agent 判断，脚本不代劳）：检查 `triggered_signals` 的 `platforms` 分布 + `examples` 的 work 分布：
  - **同账号混杂**：全部样本来自同一新号 → 可能冷启动惩罚，非 rubric 问题
  - **同平台混杂**：偏差集中在单一平台（如 13/17 来自 xhs）→ 可能该平台 baseline 偏移
  - **跨平台一致**：多平台多账号同向偏差 → rubric 维度失准证据强
  → 评估结论写入 `calibration/rubric-memo.md` → 在 Heartbeat 汇总中告知用户评估结论 + 建议（是否升级 rubric / 是否调整发布阈值）。**Agent 不得自动升级 rubric 或改阈值。**

用户不确认 → 流程到此结束，新作品继续积累新信号，同样模式再现会再触发评估。

#### 数据来源（全部从 published-track DB）

复盘时**只从 published-track DB 读取数据**，不另行抓取。`query-retro-pending.sh` 已把待复盘作品的互动数据带出，Agent 无需再查 DB 或 ls 目录。

---

## Bump — Rubric 升级（用户发起）

`rubric_notes.md` 只能由用户发起修改，Agent 只能建议。**前置**：用户在看到 Step 3b 综合评估结论后明确同意升级。

1. **生成新公式**：Agent 综合读 `rubric-memo.md` 积累的历史观察 + 评估结论，写出新打分公式（新 `rubric_notes.md` 草稿）
2. **批量盲重打**：Agent 派 blind sub-agent 对**最新发布且有数据的 10 篇**作品用新公式重打分（不足 10 篇则用全部，最少 3 篇才做验证）
3. **脚本验证**：
   ```bash
   ./skills/content-calibrator/scripts/validate-rubric.sh --new-scores /tmp/new-scores.json
   ```
   脚本复用 `detect-bump-signals` 的归一化 + 偏差检测逻辑，对这 10 篇的新分数 vs 实际数据算偏差信号。**降幅 = (旧信号数 - 新信号数) / 旧信号数 ≥ 30%（默认阈值）** → `pass=true`；否则 → `pass=false`。`--reduction-threshold` 可调阈值。旧信号数=0 时直接 fail（旧公式本无偏差，无升级必要）。
4. **pass=false** → 回到第 1 步重新生成公式，**最多 3 轮**。3 轮仍 false → 报用户"自动验证未通过，建议人工介入"
5. **pass=true → 落地**：
   - 正式写入 `calibration/rubric_notes.md`
   - 10 篇重打作品的新分数写回 DB（`cal_score_*` + `cal_rubric_version`）
   - 重打作品的 `cal_bump_evaluated` 重置为 0（新公式下应重新参与未来 bump 检测）
   - 归档 `calibration/rubric-memo.md` → `rubric-memo-v<旧版本>-<日期>.md`，按模板重置 `rubric-memo.md`
   - 更新 `.cheat-state.json` 的 `rubric_version` + `last_bump_at`

> 不做全量重打——老作品保留旧分数（历史数据），新作品按新公式打分。验证只用最新 10 篇，够代表性且成本低。

---

## 维度与权重变更规则

**维度和权重可以被修改，但必须满足以下条件之一**：
1. **用户主动要求** — "加个 XX 维度" / "把 SR 权重调到 2.0"
2. **Agent 提议 + 用户确认** — Agent 在综合评估中检测到系统性偏差后提议变更，**必须等待用户明确同意才生效**

变更流程：
- 变更维度（增/删/替换）或权重 → 走 Rubric 升级流程（生成新公式 → 盲重打 → validate-rubric.sh 验证）
- 变更被拒绝 → rubric 不动，观察记入 `rubric-memo.md`

---

## LearnFrom — 导入对标

从对标账号/爆款内容中提取 pattern，作为 rubric 初始校准信号。对标数据按平台存 `calibration/<platform>/benchmark.md`，提炼的 rubric 信号进统一 `rubric-memo.md`。

### 数据来源

1. **viral-chaser 追爆报告**：已下载的爆款视频分析 → 提取结构 pattern
2. **用户提供的数据**：手动粘贴对标账号数据
3. **published-track DB 中的历史数据**：该平台已发布内容的互动数据

### 流程

1. 确认对标来源（viral-chaser 报告 / 用户提供数据 / 历史数据）
2. 分析 pattern：哪些维度在高流量内容中一致偏高/偏低
3. 派生 rubric 信号（调整权重/维度）
4. 写入 `calibration/<platform>/benchmark.md` + 更新统一 `rubric-memo.md`

---

## Status — 校准状态看板

显示校准循环状态：

```
📊 Content Calibrator 状态

【全局 rubric】
Rubric: v0（统一）
模式: cold-start
校准池: 0 个作品
待复盘: 0 个作品

【全局阈值】每维需 >0 才放行（cal-toggle.sh --set-threshold N 修改）

【平台】
wx_mp  ✅ 已启用  baseline: 未定
xhs    ✅ 已启用  baseline: 未定

【最近复盘】
（暂无）
```

---

## 脚本

### 打分结果校验（不写入数据库）

Agent 按 rubric 打完 7 维分后，用 `score-only.sh` 校验分数合法性、计算 composite 并输出结构化 JSON，不写入 DB。此脚本不做 LLM 打分，仅校验并格式化。

```bash
./skills/content-calibrator/scripts/score-only.sh \
  --platform wx_mp \
  --content-path "output_articles/xxx/article.md" \
  --cal-er 3 --cal-hp 4 --cal-sr 4 --cal-ql 3 --cal-na 2 --cal-ab 4 --cal-pv 3
```

### 落盘打分+预测到 work 目录

blind subagent 出分 + 预测草稿后，主 agent 调 `commit-prediction.sh` 落盘。**同 work 重复调用直接覆盖** `score.json` + `prediction.md`。

```bash
./skills/content-calibrator/scripts/commit-prediction.sh \
  --work-dir "output_articles/xxx" --platform wx_mp \
  --cal-er 3 --cal-hp 4 --cal-sr 4 --cal-ql 3 --cal-na 2 --cal-ab 4 --cal-pv 3 \
  --prediction-file /tmp/prediction-draft.md
```

### 平台打分开关管理

```bash
./skills/content-calibrator/scripts/cal-toggle.sh --list
./skills/content-calibrator/scripts/cal-toggle.sh --platform wx_mp --enable
./skills/content-calibrator/scripts/cal-toggle.sh --platform wx_mp --disable
```

### 初始化平台

```bash
./skills/content-calibrator/scripts/init.sh --platform <platform_id>
```

幂等——已存在则跳过。首次调用同时创建根级统一 rubric。

### 查询 published-track 数据

```bash
./skills/content-calibrator/scripts/query-metrics.sh --platform <platform> --source-folder <folder>
```

### 构建校准池

```bash
./skills/content-calibrator/scripts/build-calibration-pool.sh
```

从 published-track DB + 各 work 的 `calibration/score.json` 构建全局校准池（per-work 归集）。

### Bump 信号检测

```bash
./skills/content-calibrator/scripts/detect-bump-signals.sh                # 默认阈值 3
./skills/content-calibrator/scripts/detect-bump-signals.sh --threshold 5  # 改阈值
```

纯 DB 操作：查 `cal_enabled=1 AND cal_bump_evaluated=0` 的记录 → 从 `cal_score_*` + 互动指标算偏差信号 → 写回 `cal_bias_signals` + `cal_bump_evaluated=1` → 聚合全量信号按维度统计同向偏差 → **触发 bump 时自动清空 `cal_bias_signals`**（未触发时保留，跨轮累积）。≥3 次同向 → bump 信号。返回结构化 JSON（含每信号的 platform 分布）。

### Rubric 升级验证（Rubric 升级流程用）

```bash
./skills/content-calibrator/scripts/validate-rubric.sh --new-scores /tmp/new-scores.json
```

`--new-scores` 指向 blind sub-agent 用新公式重打分的 JSON 文件（格式见脚本头注释）。脚本复用 `detect-bump-signals` 的 log 桶归一化 + 偏差检测逻辑，对同一批作品对比新旧公式的偏差信号数。**降幅 = (旧 - 新) / 旧 ≥ 30%（默认）** → `pass=true`；`--reduction-threshold` 可调。返回 JSON：`{pass, sample_size, old_signals, new_signals, reduction, reduction_ratio, reduction_threshold, reason}`。exit code：0=pass，1=fail。

### 导入追爆报告

```bash
./skills/content-calibrator/scripts/import-viral-chaser.sh --platform <platform> <report-path>
```
