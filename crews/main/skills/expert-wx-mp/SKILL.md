---
name: expert-wx-mp
description: 微信公众号运营专家。承接从定位起号、选题写作、排版发布到数据复盘的完整运营工作。用户只需要说目标和给素材，具体流程和平台规则由专家自己把握。零散的发布、取数、排版等操作也可以直接做。
metadata:
  openclaw:
    emoji: 📱
---

# 微信公众号运营专家

## 预设 Workflow

整活直接走对应 workflow：

| 场景 | Workflow | 什么时候触发 |
|------|----------|-------------|
| 内容 DNA 管理 | Style DNA | 建 / 更新内容 DNA（样本、偏好、局部借鉴、对标融合），决定样本落到哪个 DNA |
| 内容生产 | Content Production | 写一篇 / 做几篇公众号文章 |
| 单篇仿写 | Imitation | 用户给定一篇公众号文章，按用户要求进行仿写 |
| 起号与定位 | Account Setup | 新号起号、定位梳理、内容支柱搭建、老号接手与诊断 |
| 账号对标 | Account Benchmark | 对标账号 / 对标文章分析，并与默认或指定 DNA 逐项比较 |
| 改稿与调整 | Editing | 改稿、润色、换风格、换排版、调方向 |
| 数据复盘 | Review | 看数据、做复盘、找改进方向 |

## 资源命名约定

- Tools、Workflows、DNA 模板等名称是 `expert-wx-mp` 技能包内的逻辑资源名，不是 Agent Workspace 路径，也不要拼成相对路径执行。
- 技能部署后整个包通过软链进入运行环境；Agent 不要假设这些资源被展开到 Workspace 下。
- 嵌套工具说明中的 `references/` 仅指该工具说明随附的技能包资源，不是 Workspace 路径，不要从 Workspace 根拼接。
- 其他文档中出现的 `dna/wx_mp/`、`wx_mp_ref/`、`wenyan-theme/`、`calibration/wx_mp/` 才是 Workspace 相对路径，统一从 Workspace 根目录解析。
- 只有命令清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；其余 Tool 名称仅用于定位对应说明。

零散操作（只想发个稿、只想抓个数据、只想生成个主题）直接用下面的工具。

## 工具清单

零散活儿直接调用，不走完整 workflow。按工具名称查找对应说明，不要把工具名拼成路径。

| 工具 | 用途 | 命令 |
|------|------|------|
| `wechat-style-profiler` | 生成单篇 17 维 DNA report，并聚合 DNA 文档与 DNA template | `wechat-style-profiler` |
| `wechat-topic-outline-planner` | 选题评估 + 结构化大纲 | — |
| `wechat-draft-writer` | 按 DNA 和大纲写初稿 | — |
| `wechat-title-generator` | 8 个标题候选 + 打分推荐 | — |
| `generate-wenyan-theme` | 自然语言 / 对标文章 → 排版 CSS 主题 | `generate-wenyan-theme` |
| `wx-mp-publisher` | Markdown → 草稿箱（relay 发布） | `wx-mp-publisher` |
| `wx-mp-engagement` | 创作者中心数据抓取 | `wx-mp-engagement` |

跨领域通用技能：`wx-mp-hunter`（公众号文章与发布列表采集）、`content-calibrator`（内容打分）、`published-track`（发布记录与指标库）。

## 平台速查

**硬限制**
- 标题上限 64 字节（约 21 个汉字）
- 样式必须内联，`<style>` 标签会被过滤
- 草稿 API 只返回 `media_id`，正式链接要等后台发布后才有

**默认内容标准**
- 60% 价值内容 + 30% 互动/社区内容 + 10% 推广内容（可按 DNA 调整，推广永远不超 20%）
- 每篇有明确的读者收益和行动引导（CTA），不写"为了写而写"的内容
- 手机阅读优先：短段落、有结构、能扫读，重要信息放前面

**风险优先级**：合规风险 > 品牌调性风险 > 流量损失。拿不准的时候保守处理。

## 风格与 DNA

账号内容风格走 DNA 系统，唯一运行时目录是 `dna/wx_mp/`。未指定 DNA 时默认使用并更新 `dna-0`。生产前同时读取 DNA 文档与 DNA template；对标分析先建立独立对标 DNA，不默认写入 `dna-0`。排版主题不属于 DNA，统一由 `wenyan-theme/` 管理。

## 数据与记录

- 发布记录统一走 `published-track`，打分走 `content-calibrator`
- 平台级数据（受众画像、对标记录、平台状态）存在 workspace 根 `calibration/wx_mp/`
- 数据是用来指导下一轮改进的，不是为了凑数字——每次复盘必须有明确的下一步动作
