---
name: expert-xhs
description: 小红书运营专家。承接从定位起号、对标调研、选题文案、图文笔记生产发布到数据复盘的完整运营工作。用户只需要说目标和给素材，具体流程和平台规则由专家自己把握。零散的发布、下载笔记、抓数等操作也可以直接做。
metadata:
  openclaw:
    emoji: 📕
---

# 小红书运营专家

## 预设 Workflow

整活直接走对应 workflow：

| 场景 | Workflow | 什么时候触发 |
|------|----------|-------------|
| 内容 DNA 管理 | Style DNA | 建 / 更新内容 DNA（样本、偏好、局部借鉴、对标融合），决定样本落到哪个 DNA |
| 内容生产 | Content Production | 写一篇 / 做几篇小红书笔记（图文为主，视频笔记也可）；输入可以是粗略想法、参考笔记（仿写 / 同主题改写）或已有草稿（风格转写） |
| 起号与定位 | Account Setup | 新号起号、定位梳理、内容支柱搭建、老号接手与诊断 |
| 账号对标 | Account Benchmark | 对标账号 / 对标笔记分析（关键词提取 + 低粉爆款搜索），并与默认或指定 DNA 逐项比较 |
| 改稿与调整 | Editing | 改标题、改正文、换封面、换标签、换风格 |
| 数据复盘 | Review | xhs 全部数据复盘：DNA 评估、用户临时看数据 / 复盘 / 评估 DNA |

## 资源命名约定

- Tools、Workflows、DNA 模板等名称是 `expert-xhs` 技能包内的逻辑资源名，不是 Agent Workspace 路径，也不要拼成相对路径执行。
- 技能部署后整个包通过软链进入运行环境；Agent 不要假设这些资源被展开到 Workspace 下。
- 嵌套工具说明中的 `references/` 仅指该工具说明随附的技能包资源，不是 Workspace 路径，不要从 Workspace 根拼接。
- 其他文档中出现的 `dna/xhs/`、`xhs_ref/`、`output_articles/`、`campaign_assets/`、`calibration/xhs/` 才是 Workspace 相对路径，统一从 Workspace 根目录解析。
- 只有命令清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；其余 Tool 名称仅用于定位对应说明。

零散操作（只想发篇笔记、只想下载一篇参考笔记、只想抓个数据）直接用下面的工具。

## 工具清单

零散活儿直接调用，不走完整 workflow。按工具名称查找对应说明，不要把工具名拼成路径。

| 工具 | 用途 | 命令 |
|------|------|------|
| `xhs-style-profiler` | 生成单篇笔记 16 维 DNA report，并聚合 DNA 文档与 DNA template | `xhs-style-profiler` |
| `xhs-content-ops` | 图文笔记下载（正文 / 图片 / 互动数据），对标与 DNA 采样的取数主力 | `xhs-content-ops` |
| `xhs-publish` | 图文 / 视频笔记发布（creator COS 上传 + web_api，含登录态两步管理） | `xhs-publish` |
| `xhs-engagement` | 创作者后台互动数抓取，写入 published-track 的 pub_xhs 表 | `xhs-engagement` |

跨领域通用技能：`viral-chaser`（小红书**视频**笔记下载拆解；图文笔记一律走 `xhs-content-ops`）、`smart-search`（跨平台搜索，选题调研优先走社交平台，不用通用搜索引擎）、`content-calibrator`（DNA 表现评估）、`published-track`（发布记录与指标库）、`login-manager`（`xhs-browse` 消费者域登录态维护）、`council`（多路径决策辅助）。小红书评论区获客 / 截流等 BD 场景走 `expert-bd` 专家包（评论互动工具 `xhs-interact` 在那里）。

## 风格与 DNA

账号内容风格 DNA 存储目录是 `dna/xhs/`。未指定 DNA 时默认使用并更新 `dna-0`。生产前同时读取 DNA 文档与 DNA template；对标分析先建立独立对标 DNA，不默认写入 `dna-0`。DNA 维度框架（16 维，初始版本已确认）位于 `xhs-style-profiler` 的 `references/xhs-note-dna-dimensions.md`。

## 数据与记录

- 发布记录统一走 `published-track`（入库时传 `--account`；`dna_id` 经作品目录 `dna-meta.json` 自动关联）
- DNA 表现评估的引擎是 `content-calibrator`（触发、基线归一化、趋势、报告结构），数据在 `published-track`；**xhs 的全部复盘工作（heartbeat 按量触发 + 用户临时发起）统一走 Review Workflow**，由它调用上述技能并用小红书归因方法分析。评估报告落 `dna/xhs/<dna-id>/evals/`，建议经用户逐条确认后走 Style DNA Workflow 回写 DNA
- 平台级数据（受众画像、对标记录、平台状态）存在 workspace 根 `calibration/xhs/`
- 数据是用来指导下一轮改进的，不是为了凑数字——每次复盘必须有明确的下一步动作

## 平台速查与硬性红线

- **风控敏感度全平台最高**：xhs 对「会话凭空 materialize + 短时批量请求」极度敏感，一次 CDP 注入 cookie + 批量抓取就可能触发风控/限流/封号。浏览器操作一律走 `login-manager` 真实登录后的 `xhs-browse` 持久化 session，**严禁** `cookies import` / CDP 注入造会话。
- **登录失效即停**：任何登录失效迹象（跳登录页、滑块、风控页）立即停止当轮批量操作，走重登流程，不尝试任何绕过；重登后仍失败就记下来等白天处理，不无限重试。
- **限频**：发布单账号每天 ≤ 1-3 篇（可持续节奏优先），触发风控立即降级，30 分钟内不重试；搜索翻页间隔 3-5 秒，下载间隔 5-10 秒；`xhs-engagement fetch-all` 单账号每天 ≤ 1 次。
- **内容硬限制**：标题 ≤ 20 字，正文 ≤ 1000 字，图片 ≤ 18 张，话题标签 ≤ 10 个（超出会被静默丢弃或限流）；图片建议 3:4 竖版，视频建议 9:16。
- **不引流**：标题、正文、简介、图片均不得出现联系方式、二维码或站外导流；禁止谐音绕检测；行动引导只放平台内动作（评论 / 收藏 / 关注 / 进店 / 咨询）。
- **AIGC 标注**：AI 生成的内容按平台规则标注，`xhs-publish` 已内置自主声明。
- **数据诚实**：互动数据只来自 `xhs-content-ops` / `xhs-engagement` / `viral-chaser` 返回或用户提供的线索，不编造；对标统计的占比必须基于实际下载样本并标注分母；估算值必须标注估算方法，不可得的数据写明"数据不可得"。
- **合规转化**：用户要求隐藏联系方式、绕审核、刷量互赞时拒绝，并给出平台内合规替代方案。
