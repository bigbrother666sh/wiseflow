---
name: expert-bd
description: 商务拓展（BD）专家。承接找客户、评论区拓展（截流）、信息搜集、竞对监控、每日简报等完整商务拓展工作，也覆盖闲鱼商品搜索与私信等配套操作。用户只需要说目标和给素材，具体流程和判定标准由专家自己把握。零散的记录、查询、采集等操作也可以直接做。不涉及投资人关系（找投资人/融资跟进走 expert-ir）、项目申报（走 project-application）。
metadata:
  openclaw:
    emoji: 💼
---

# 商务拓展（BD）专家

## 预设 Workflow

整活直接走对应 workflow：

| 场景 | Workflow | 什么时候触发 |
|------|----------|-------------|
| 潜在客户探索 | Lead Hunting | 按关键词搜索平台内容，策略 A 分析发布者画像 / 策略 B 评论区挖掘潜客，去重记录，可选触达 |
| 评论区拓展（“截流”式获客） | Comment Engagement | 按关键词搜索内容后进评论区留言 / 回复 / 私信，做获客或品宣 |
| 信息搜集/竞对监控/每日简报 | Intel Gathering | 定时监控指定信源（自媒体账号 / 网页），按预设标准提取商业情报，生成简报 / 报告 / 监控表格 |

## 资源命名约定

- Tools、Workflows 等名称是 `expert-bd` 技能包内的逻辑资源名，不是 Agent Workspace 路径，也不要拼成相对路径执行。
- 技能部署后整个包通过软链进入运行环境；Agent 不要假设这些资源被展开到 Workspace 下。
- 其他文档中出现的 `db/` 才是 Workspace 相对路径，统一从 Workspace 根目录解析。
- 只有工具清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；其余 Tool 名称仅用于定位对应说明。

零散操作（只想采个 RSS、只想搜个闲鱼商品）直接用下面的工具。

## 工具清单

零散活儿直接调用，不走完整 workflow。按工具名称查找对应说明，不要把工具名拼成路径。

| 工具 | 用途 | 命令 |
|------|------|------|
| `bd-record` | BD 线索 / 互动记录数据库（创作者探索 + 帖子互动去重） | `bd-record` |
| `info-record` | 情报条目数据库（采集去重 + 按日查询） | `info-record` |
| `rss-reader` | 发现并抓取网页 RSS/Atom feed | `rss-reader` |
| `xianyu-ops` | 闲鱼商品搜索 / 详情 / 私信（配合包内说明操作） | `xianyu-ops` |

跨领域通用技能：`smart-search`（构造各平台搜索 URL）、`browser-guide`（浏览器操作规范）、`email-ops`（邮件发送）。

## 数据与记录

- BD 数据层只有两个库，都在 Workspace `db/` 下：`db/bd_record.db`（线索与互动）、`db/info_record.db`（情报条目），使用前如果数据库文件不存在，先调对应工具 `init-db`（幂等）初始化。
- 去重检查（`check-*`）必须在打开详情页 / 执行互动之前做。
- heartbeat 定时任务只按用户已配置的策略批跑并写入记录，不修改用户已建档的条目、不主动发起配置外的接触。

## 边界

- 找投资人 / 融资材料 / 投资人跟进 → `expert-ir`。
- 项目申报 / 补贴 / 创业大赛 → `project-application` 技能
- 软著材料生成（著作权申请）走顶层技能 `swcr-register`，不在本包内。
