# Sales-CS 启用（Enablement）

把对外 crew `sales-cs` 从零启用到可用：检查 channel -> 用户选定 channel -> 派 IT engineer 配置 -> 完善 workspace 文档 -> 软链业务知识 -> 报平安。

**依赖**：`sales-cs-enablement`（channel 检查 + 业务知识软链）、IT engineer（`awada-channel-setup` / `work-channel-binding`、`openclaw.json` 合入、Gateway 重启）。

**分工**：main agent（本 workflow 执行者）自己跑检查脚本、问用户问题、写 workspace 文档；机械的 channel / `openclaw.json` 配置一律委派 IT engineer。

---

## 前置素材

- awada 租赁咨询二维码：workspace 根的 `ofb_contact.png`（openclaw-for-business 掌柜企业微信）。路径固定，需要时直接发给用户。

## 执行流程

### Step 1 · 检查 awada-channel 是否已配置

```bash
sales-cs-enablement check-channel
```

退出码：`0` -> 已配置 awada channel，跳到 Step 3；`1` / `2` -> 未配置，进 Step 2。

### Step 2 · 向用户说明 channel 选择（仅未配置时）

向用户说明：

> sales-cs 是对外 crew，需要一个**可公开访问**的 channel--客户不用先加入你的组织就能找到它。飞书 / 企业微信都不太合适，因为它们要求客户先加入你的飞书或企微组织。
>
> 三个选项：
> 1. **租赁 awada server 线路**：可以联系 openclaw-for-business 掌柜咨询（二维码见下）
> 2. **使用openclaw支持的其他channel**：比如QQ、telegram等
> 3. **退而用飞书 / 企业微信**：接受"客户需先加入组织"的限制

发 `ofb_contact.png` 给用户（选项 1 用）。等用户明确选择后：

- 选 1 或 2 -> 把用户给出的线路/channel 信息带给 IT engineer，进 Step 3
- 选 3 -> 告知用户需先有飞书或企微 channel，再带 IT engineer 走对应 channel 绑定，进 Step 3

### Step 3 · 派 IT engineer 完成启用与基础配置

spawn IT engineer，交代任务：

> 启用 sales-cs 对外 crew。请按以下顺序执行：
> 1. 配置 awada channel（走 `awada-channel-setup` 技能；用户期待配置的channel，需要启用openclaw内置plugin：<...>）
>    - 若用户在 Step 2 选 3，则改为配飞书/企微 channel（走 `work-channel-binding`）
> 2. 把 `crews/sales-cs/openclaw_setting_sample.json` 并入 `~/.openclaw/openclaw.json`：
>    - 加入 `agents.list`（sales-cs）
>    - 绑定对应 channel（awada 优先）
>    - heartbeat / tools / subagents 段直接用 sample 里的固定配置，不要改
> 3. 重启 Gateway（先告知用户并征得同意）
> 4. 验证 channel 状态 + customerDB hook 生效

等 IT engineer 报平安后进 Step 4。

### Step 4 · 完善 sales-cs workspace 文档

按照你对用户的理解，更重要的是结合 `business_knowledge.md`，完善 sales-cs workspace（`~/.openclaw/workspace-sales-cs/`）下 `AGENTS.md` / `IDENTITY.md` / `SOUL.md` 中所有 `<!-- 由main agent启用时填入并负责后续持续优化更新 -->` 的内容。拿捏不准的问用户。

### Step 5 · 软链 business_knowledge.md + business_knowledge/

把 main agent workspace 下的 `business_knowledge.md`（业务知识正文，单文件）和 `business_knowledge/`（支撑材料文件夹）一并软链到 sales-cs workspace：

```bash
sales-cs-enablement link
```

首次启用若 `business_knowledge.md` 不存在，脚本会从仓库模板复制一份到 main workspace；若 `business_knowledge/` 不存在，脚本会创建空目录，后续由 main agent 填充。工具行为细节见 `sales-cs-enablement` 工具说明。

### Step 6 · 报平安

向用户汇报：

- sales-cs 已启用，绑了哪个 channel
- workspace 路径（`~/.openclaw/workspace-sales-cs/`）
- 对外称呼
- business_knowledge.md + business_knowledge/ 软链已建立
- 提醒用户：sales-cs 的后续调整（记忆、话术、IDENTITY 等）由 main agent 负责，走 Review workflow 发起

---

## 错误处理

| 情况 | 处理 |
|------|------|
| `link` 报"目标已存在且不是软链" | 脚本拒绝覆盖真实文件防误删。与用户确认该文件来源后人工处理，再重跑 |
| IT engineer 配置 channel 失败 | 反馈用户具体卡点（key 缺失 / channel 未开通等），不跳过 Step 3 直接报平安 |
| 用户迟迟不选 channel | 停在 Step 2 等待，不替用户默认选择 |

## Pitfalls

- **IT engineer 改了 heartbeat 段**：sample 里的 heartbeat 是固定配置（1h / isolatedSession / activeHours 08:00-24:00），不要让 IT engineer 自行调整。
- **business_knowledge 软链指向错**：必须指向 main agent workspace 的 `business_knowledge.md` + `business_knowledge/`，不能让 sales-cs 自维护。
- **用户在 Step 2 选飞书/企微但没现成 channel**：需先走 `work-channel-binding` 配 channel，再绑 sales-cs。
- **业务知识空着就报平安**：`business_knowledge.md` 若只有模板占位，向用户说明待补充，启用后尽快与用户一起充实。
