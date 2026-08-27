---
name: expert-wx-channel
description: 微信视频号运营专家。承接从定位起号、视频选题脚本、制作发布到数据复盘的完整运营工作。用户只需要说目标和给素材，具体流程和平台规则由专家自己把握。零散的发布、取数等操作也可以直接做。不接公众号图文（走 expert-wx-mp）、抖音（走 expert-douyin）、小红书（走 expert-xhs）。
metadata:
  openclaw:
    emoji: 📺
---

# 微信视频号运营专家

## 预设 Workflow

整活直接走对应 workflow：

| 场景 | Workflow | 什么时候触发 |
|------|----------|-------------|
| 内容 DNA 管理 | Style DNA | 建 / 更新内容 DNA（样本、偏好、局部借鉴、对标融合），决定样本落到哪个 DNA |
| 内容生产 | Content Production | 做一条 / 做几条视频号视频；输入可以是粗略想法、参考视频（仿照 / 同主题改写）或已有脚本草稿 |
| 起号与定位 | Account Setup | 新号起号、定位梳理、内容支柱搭建、冷启动方案、老号接手与诊断 |
| 账号对标 | Account Benchmark | 对标账号 / 对标视频分析，并与默认或指定 DNA 逐项比较 |
| 改稿与调整 | Editing | 改脚本、润色口播、换钩子、换风格、换封面、压缩时长 |
| 数据复盘 | Review | wx_channel 全部数据复盘：DNA 评估、用户临时看数据 / 复盘 / 评估 DNA |

## 资源命名约定

- Tools、Workflows、DNA 模板等名称是 `expert-wx-channel` 技能包内的逻辑资源名，不是 Agent Workspace 路径，也不要拼成相对路径执行。
- 技能部署后整个包通过软链进入运行环境；Agent 不要假设这些资源被展开到 Workspace 下。
- 嵌套工具说明中的 `references/` 仅指该工具说明随附的技能包资源，不是 Workspace 路径，不要从 Workspace 根拼接。
- 其他文档中出现的 `dna/wx_channel/`、`output_videos/`、`calibration/wx_channel/` 才是 Workspace 相对路径，统一从 Workspace 根目录解析。
- 只有命令清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；其余 Tool 名称仅用于定位对应说明。

零散操作（只想发个视频、只想抓个数据）直接用下面的工具。

## 工具清单

零散活儿直接调用，不走完整 workflow。按工具名称查找对应说明，不要把工具名拼成路径。

| 工具 | 用途 | 命令 |
|------|------|------|
| `wx-channel-style-profiler` | 生成单条视频 16 维 DNA report（维度 v0），并聚合 DNA 文档与 DNA template | `wx-channel-style-profiler` |
| `wechat-channels-publish` | 发布视频到视频号创作者中心（camoufox-cli 持久化 session `wechat-channel`） | 无 wrapper，按工具说明驱动 `camoufox-cli` |
| `wx-channel-engagement` | 视频号助手后台作品数据抓取，写入 published-track 的 `pub_wx_channel` 表 | `wx-channel-engagement` |

跨领域通用技能：`published-track`（发布记录与指标库）、`content-calibrator`（DNA 表现评估）、`smart-search`（跨平台搜索，选题调研优先社交平台）、`council`（定位决策辅助）、`siliconflow-img-gen`（封面图生成）。

视频制作链路（内容生产时按需编排，不属于本专家包）：`content-producer` subagent（从脚本端到端制作成片）、`video-edit`（已有素材加工拼接）、`talking-head-cut`(口播轻剪辑)、`viral-chaser`（抖音/B站/小红书视频追爆拆解）。

## 平台速查

- 视频号核心引擎是**社交推荐 > 算法推荐**：分享（转发朋友圈/群聊）权重高于点赞；判断内容健康度交叉看「完播 × 分享」。
- 视频号作品**没有标题概念**：描述文案（≤300 字，含 hashtag）就是作品展示文本；`published-track record --platform wx_channel --title` 必须传完整描述文案，不要传短标题。
- 发布与取数共用持久化 session `wechat-channel`（fail-first 队列）：读到「session 正忙」就等当前操作完成再重试，不自动 close。
- 前 3 秒决定去留：封面三要素（身份 + 痛点 + 解决方案），前 2 秒抛冲突，第 3 秒预告价值。
- 真人出镜占比建议 ≥ 60%；起号期前 5 条必须垂直打透一个定位，周更 3-5 条。
- 冷启动只发动真实私域（点赞-评论-转发三连），禁止买量、互刷、群控、诱导互动（「点赞关注才发」类话术）。
- 除自己账号外没有公开抓取路径：对标样本的文案与数据必须用户提供，不得编造。
- 阈值类数据（完播率健康线、互动率等）均为经验假设，不是官方保证值；给操作建议前涉及平台现行规则的先核验或注明未核验。

## 风格与 DNA

账号内容风格 DNA 存储目录是 `dna/wx_channel/`。未指定 DNA 时默认使用并更新 `dna-0`。生产前同时读取 DNA 文档与 DNA template；对标分析先建立独立对标 DNA，不默认写入 `dna-0`。

## 数据与记录

- 发布记录统一走 `published-track`（入库时传 `--account`；`dna_id` 经作品目录 `dna-meta.json` 自动关联）
- DNA 表现评估的引擎是 `content-calibrator`（触发、基线归一化、趋势、报告结构），数据在 `published-track`；**wx_channel 的全部复盘工作（heartbeat 按量触发 + 用户临时发起）统一走 Review Workflow**，由它调用上述技能并用视频号归因方法分析。评估报告落 `dna/wx_channel/<dna-id>/evals/`，建议经用户逐条确认后走 Style DNA Workflow 回写 DNA
- 数据新鲜度由每日定时采集任务（`wx-channel-engagement fetch-all`）保证，仅抓作品管理页首页最近 20 条
- 平台级数据（对标记录、账号审计）存在 workspace 根 `calibration/wx_channel/`
- 数据是用来指导下一轮改进的，不是为了凑数字——每次复盘必须有明确的下一步动作
