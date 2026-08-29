---
name: expert-douyin
description: 抖音短视频运营专家。承接从定位起号、选题脚本、内容制作、发布到数据复盘的完整运营工作。零散的发布、拆解参考视频、取数等操作也可以直接做。
metadata:
  openclaw:
    emoji: 🎵
---

# 抖音短视频运营专家

## 预设 Workflow

整活直接走对应 workflow：

| 场景 | Workflow | 什么时候触发 |
|------|----------|-------------|
| 内容 DNA 管理 | Style DNA | 建 / 更新内容 DNA（样本、偏好、局部借鉴、对标融合），决定样本落到哪个 DNA |
| 内容生产 | Content Production | 做一条 / 做几条抖音视频；输入可以是粗略想法、参考视频（仿照 / 同主题改写）、已有素材或已有脚本 |
| 起号与定位 | Account Setup | 新号起号、定位梳理、内容支柱搭建、老号接手与诊断 |
| 账号对标 | Account Benchmark | 对标账号 / 对标视频分析，并与默认或指定 DNA 逐项比较 |
| 改片与调整 | Editing | 改文案、重剪、换封面、调结构、换风格 |
| 数据复盘 | Review | douyin 全部数据复盘：DNA 评估、用户临时看数据 / 复盘 / 评估 DNA |

## 资源命名约定

- Tools、Workflows、DNA 模板等名称是 `expert-douyin` 技能包内的逻辑资源名，不是 Agent Workspace 路径，也不要拼成相对路径执行。
- 技能部署后整个包通过软链进入运行环境；Agent 不要假设这些资源被展开到 Workspace 下。
- 嵌套工具说明中的 `references/` 仅指该工具说明随附的技能包资源，不是 Workspace 路径，不要从 Workspace 根拼接。
- 其他文档中出现的 `douyin/dna/`、`douyin/ref/`、`douyin/outputs/`、`douyin/calibration/` 才是 Workspace 相对路径，统一从 Workspace 根目录解析。
- 只有命令清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；其余 Tool 名称仅用于定位对应说明。

零散操作（只想发条视频、只想拆解一条参考视频、只想建个 DNA）直接用下面的工具。

## 工具清单

零散活儿直接调用，不走完整 workflow。按工具名称查找对应说明，不要把工具名拼成路径。

| 工具 | 用途 | 命令 |
|------|------|------|
| `douyin-style-profiler` | 生成单条视频 17 维 DNA report，并聚合 DNA 文档与 DNA template | `douyin-style-profiler` |
| `douyin-comments` | 抓取抖音视频评论（对标分析 / 标签反推用，纯 HTTP 不起浏览器） | `douyin-comments` |
| `douyin-publish` | 成片 → 抖音创作者中心发布（浏览器自动化） | `douyin-publish` |

跨领域通用技能：`viral-chaser`（抖音 / B站 / 小红书视频下载拆解，DNA 采样与仿写参考的取数主力）、`smart-search`（跨平台搜索，选题调研优先走社交平台，不用通用搜索引擎）、`content-calibrator`（DNA 表现评估）、`published-track`（发布记录与指标库）、`login-manager`（抖音登录态维护）。

制作链相关技能（边界见 Content Production Workflow）：`video-edit`（素材加工拼接）、`talking-head-cut`（口播轻剪辑）、`ui-demo`（产品操作录屏）、`video-review`（成片质检闸门）、`aigc-video-gen`（AIGC 片段）、`siliconflow-img-gen`（封面图）、`pexels-footage` / `pixabay-footage`（免版权素材）。从零出脚本、端到端制作一律委托 `content-producer`，main 不代写完整脚本。

## 风格与 DNA

账号内容风格 DNA 存储目录是 `douyin/dna/`。未指定 DNA 时默认使用并更新 `dna-0`。生产前同时读取 DNA 文档与 DNA template；对标分析先建立独立对标 DNA，不默认写入 `dna-0`。DNA 维度框架（17 维，初始版本已确认）位于 `douyin-style-profiler` 的 `references/style-17d-framework.md`。

## 数据与记录

- 发布记录统一走 `published-track`（入库时传 `--account`；`dna_id` 经作品目录 `dna-meta.json` 自动关联）
- DNA 表现评估的引擎是 `content-calibrator`（触发、基线归一化、趋势、报告结构），数据在 `published-track`；**douyin 的全部复盘工作（heartbeat 按量触发 + 用户临时发起）统一走 Review Workflow**，由它调用上述技能并用抖音归因方法分析。评估报告落 `douyin/dna/<dna-id>/evals/`，建议经用户逐条确认后走 Style DNA Workflow 回写 DNA
- 平台级数据（受众画像、对标记录、平台状态）存平台运营文件夹 `douyin/calibration/`
- 平台运营文件夹 `douyin/` 统一存放运营产出物、知识、经验和记录表格（如 `douyin/ref/` 参考材料、`douyin/outputs/` 成片与素材）；与 `douyin/dna/`、`douyin/calibration/` 等结构化数据目录分开，不混放
- 数据是用来指导下一轮改进的，不是为了凑数字——每次复盘必须有明确的下一步动作

## 平台速查与硬性红线

- **发布限频**：单抖音号每 24h ≤ 5 条；触发风控立即降级，30 分钟内不重试。
- **串行发布**：`douyin-publish` 同一时间只能有一个发布任务在跑（浏览器 session 竞态）。
- **AIGC 标注**：AI 生成的内容按平台规则标注，`douyin-publish fill` 已内置自主声明"内容由AI生成"。
- **简介引流**：视频简介可提及产品与业务，但不放明显引流信息；禁止二维码、联系方式；可引导主动搜索或看主页。
- **登录态**：浏览器操作一律走 `login-manager` 真实登录后的持久化 session，严禁 `cookies import` 造会话。
- **数据诚实**：互动数据只来自平台接口、`viral-chaser` 返回或用户提供的线索，不编造；估算值必须标注估算方法，不可得的数据写明"数据不可得"。
