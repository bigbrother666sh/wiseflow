# openclaw 2026.9.3 升级事实调研

> 落盘 2026-09-11 · 调研窗口 2026-09-10 06:23 – 2026-09-11 07:30（CST）
> 当前基座：`2026.7.1-2`（`0790d9f593ad30c940ed93b5872a8cf6d6f3cf8c`，pin 在仓根 `openclaw.version`）
> 调研目标：`2026.9.3`（`1391f7cd2d4`，tag `v2026.9.3`）；过渡候选：`extended-stable/2026.7.33`（tip `f619d7a9fa3`）
> **本文只记事实与实测数据，不做决策**；待拍板项集中在 §10，施工方案另开文档。
> 相关：[browser-stack-replacement-spec-2026-07.md](./browser-stack-replacement-spec-2026-07.md)（camoufox 双线栈 spec）、[browser-extension-replacement-research.md](./browser-extension-replacement-research.md)、`patches/browser-camoufox-pivot/README.md`

## 证据口径

| 标记 | 含义 |
|---|---|
| `[A]` | 2026-09-10 早会话内实测（pristine worktree `/tmp/oc93` 逐个 `git apply`、`git log --grep`、`ls-tree`），**本次落盘未复验**，仅记录当时结论 |
| `[B]` | 2026-09-11 落盘时在 `/home/wukong/wiseflow/openclaw` 用 `v2026.7.1-2` / `v2026.9.3` 两个 tag 现场实测（可复跑，命令见附录 A） |
| `[C]` | 上游文档 / release notes 原文（路径 + 行号以 9.3 tag 为准） |

---

## 0. 摘要（先读这段）

1. **不是"切版本 + 验 patch"能过的升级**：`v2026.7.1-2` **不是** `v2026.9.3` 的祖先，merge-base = `b81666ca6af`（2026-07-08），9.3 侧 **24,853** commits、7.1-2 侧独有 **224** `[B]`（今早 `[A]` 的数字已复算一致）。37 个 patch 里 **30 个要重做**（3777/4240 行），其中 9 个删除型 patch **全部硬失败** `[A]`。
2. **awada 插件在 9.3 会加载即死**：`src/plugin-sdk/index.ts` 被删（裸导入 `openclaw/plugin-sdk` 从 exports 消失），`ClawdbotConfig` 全仓 0 命中（改名 `OpenClawConfig`）`[A]`。这是生产链路，优先级最高。
3. **工具链硬门槛**：9.3 `engines.node = >=24.16.0 <25 || >=26.1.0`（**Node 22 / 25 支持被整条砍掉**），`packageManager = pnpm@12.3.4` `[B]`；我们 `build-dist.yml` 还锁 `24.15.0`（5 处）`[B]`。
4. **用户两项核心诉求都不在 extended-stable/2026.7.33 上**：①发现本机已装 codex/claude code 当 provider（最低要 **9.1**）、②更低对话 token 消耗（要拿满得 **9.3**）`[A]`。→ ES 7.33 只能当过渡，不能当终点。
5. **浏览器子系统在 9.3 是一次重写**：`extensions/browser` **567 files changed（+100,528 / −23,896）**，其中新增 263 / 修改 286 / 删除 18 `[B]`；工具入口 `browser-tool.ts` 从 1087 行缩到 439 行并被拆成 8 个模块 `[B]`。
6. **浏览器协议层没有第四种**：仍是「自管 CDP / Chrome DevTools MCP / Chrome 扩展 relay」三种，且 **7.1-2 已全有** `[B][C]`。但 9.x 新增了两种**控制面**：Computer Use（`extensions/cua-computer`，0 → 39 文件）与 cloud worker 的 attached browser runtime（`src/worker/`，0 → 68 文件）`[B]`。
7. **9.3 的浏览器新形态对我们几乎全是无关面**（extension / existing-session 要真人 Chrome，CUA 要 Mac/Windows，worker 是云场景）；真正有用的只有 `navigate` 内联 snapshot、`text`/`requests`/`errors`、能力裁剪三项——**都指向省 token / 省轮次** `[B][C]`。
8. **已落地动作**：第三方插件 pin 已 bump（`openclaw-weixin` 2.4.6→2.4.8、`wecom-openclaw-cli` 1.1.0→1.1.1，commit `d5e112c`，已推 origin/master）；**基座 pin 一行未动** `[B]`。
9. **量级估算**：4.5–7 人日（patch re-port 2–3.5 / awada 0.5–1 / 工具链 0.5 / 配置+doctor 0.5–1 / build+tsgo+冒烟 1）`[A]`。

---

## 1. 版本线拓扑 `[A]`，其中祖先关系 / commit 计数 / ES tip 已于 `[B]` 复验

| 线 | ref | 最新 commit | 状态 |
|---|---|---|---|
| 我们现在用的 | tag `v2026.7.1-2` = `origin/release/2026.7.1` 分支 tip | 2026-07-18（8/4 发布） | **已冻结**，不会再动 |
| 延长稳定 7.x | `origin/extended-stable/2026.7.33` | `f619d7a9fa3`（2026-09-09）`[B]` | **活跃维护中**，版本号 2026.7.33 |
| 延长稳定 6.x | `origin/extended-stable/2026.6.33`（tag 6.33/6.34） | 2026-09-08 | 活跃；npm `extended-stable` dist-tag 当前指向 **2026.6.34** |
| 主稳定线 | `release/2026.8.1 → 8.2 → 9.1 → 9.2 → 9.3` | 2026-09-07/08 | 火车式，一周 1–2 个稳定版 |

关键事实：

- **`v2026.7.1-2` 是 `extended-stable/2026.7.33` 的直系祖先**（`git merge-base --is-ancestor` = **YES**），`git rev-list --count v2026.7.1-2..origin/extended-stable/2026.7.33` = **38**，我们侧 0 个独有 commit `[B]`。
- **`v2026.7.1-2` 不是 `v2026.9.3` 的祖先**（`--is-ancestor` = **NO**）：merge-base = `b81666ca6af`（2026-07-08，`Fix container image upgrade migrations before gateway readiness (#101881)`）；9.3 侧 **24,853** commits，7.1-2 侧独有 **224** 个（多为 CI/QA）`[B]`。
- 我们当年靠 7.1-1 / 7.1-2 拿到的修复**已随主线进 9.3**（按 PR 号核到：#108487 codex progress、#108652 memory sidecar、#108258 WSL EROFS、#107294 npm lock、#106065 SQLite WAL、#108336 plugin metadata）→ **没有丢修复** `[A]`。
- **7.33 当时还没打 tag、没发 npm 包**（分支上全是 `package acceptance` / `release preflight` / `frozen upgrade baselines` 类收尾 commit）`[A]`。
- 6.33/6.34 与 7.1-2 是**分叉**关系（merge-base 6/24，它侧 332 commit），我们 37 个 patch 里 **17 个目标文件已漂移** → 功能倒退 + 还要重做 patch，**不可选** `[A]`。
- 上游文档明确：`openclaw update --channel extended-stable` **只对 package 安装生效，git checkout 会被拒**（`docs/install/development-channels.md:43`、`docs/install/updating.md:42-43`）`[C]`。我们是源码 clone + commit pin + 自己 build，所以对我们只是"pin 哪棵树"的问题，但意味着**不能靠 CLI 自动跟，必须自己 re-pin**（巡检项）。

### 1.1 `package.json` 硬指标对比 `[B]`

| 字段 | v2026.7.1-2 | v2026.9.3 |
|---|---|---|
| `version` | 2026.7.1 | 2026.9.3 |
| `engines.node` | `>=22.22.3 <23 \|\| >=24.15.0 <25 \|\| >=25.9.0` | **`>=24.16.0 <25 \|\| >=26.1.0`** |
| `packageManager` | `pnpm@11.2.2` | **`pnpm@12.3.4`** |

> Node 22 与 25 两条线在 9.3 被整体移除；上游同时说明 Node 22/25/更早 24.x 存在 **SQLite 文本截断**问题（数据损坏级）`[A]`。

---

## 2. 中间版本功能差异（7.1-2 → 9.3）`[A][C]`

| 版本 | 发布 | 新功能要点 | 破坏性 |
|---|---|---|---|
| **8.1**（= OpenClaw 2.0） | 8/31 | 重建 Web 体验、onboarding 简化、memory/session 连续性、历史对话搜索、跨设备/云 worker 会话、durable 进度卡片、结构化提问卡片、chat 内 widgets/dashboards、私密凭据请求（masked prompt）、automation permission、音视频保真；**浏览器与 Computer Use 大改**（见 §7） | OpenProse 移除；`codex/*` → `openai/*` 路由迁移；显式 `modelPolicy.allow`；named agent（`main` 语义变化）；**Skill Workshop + 自动自学习**；plugin SDK 子路径弃用（9/1 移除门） |
| **8.2** | 9/1 | Linux 桌面 companion、Home dock、后台会话、**无 Gateway 也能浏览器控制**（扩展唤醒本地 relay）、4 套主题；可靠性「回复要把活干完」（settled tool work 之后给最终答案、accepted turn 之后暴露失败） | — |
| **9.1** | 9/3 | Mermaid 图、Android 补齐、更新恢复更安全、长对话/大安装开销降低；**quick-start lane 检测本机已有 Claude Code/Codex 登录与 API key 并 live 校验**；standalone agent 浏览器 host-first 默认 | 见 §7.6-4 |
| **9.2** | 9/5 | **回复在 Gateway 重启后能恢复**（active/queued/delegated）、升级保留 active settings/enabled skills/default-agent 归属、GPT-6 Astra、备份保数据（NUL/拒绝损坏归档）、**改设置不用重启** | — |
| **9.3** | 9/8 | 更新预演（隔离候选态）、性能（保住 warm prompt cache、冷会话与记忆搜索少做功、worker build 复用）、Skill Workshop 技能改 agent-owned collection | **Node ≥24.16/≥26.1**；exec-policy/approval/SDK 别名；Find/Grep & Ls 结果回调字段；retire `allowSymlinkTargetWrites` |

上游 release notes 位置 `[C]`：`docs/releases/2026.8.1/browser-and-computer-use.md`（401 行，浏览器专项）、`docs/releases/2026.9.1.md:1483-1493`（Browser and Computer Use）、`docs/releases/2026.9.2.md:2759-2771`、9.3 见仓根 `CHANGELOG.md`（未单独出 `docs/releases/2026.9.3.md`）。

---

## 3. Patch 迁移实测 `[A]`

在 `/tmp/oc93` pristine worktree 里逐个独立 `git apply`（37 个 patch = `patches/002`、`patches/007` + `patches/browser-camoufox-pivot/patches/01-35`）：

| 结果 | 数量 | 明细 |
|---|---|---|
| 干净应用 | **7** | 5 个 plain clean + 2 个靠 `--3way` 兜住（`01-mod-docs--tools--browser`、`13-mod-openclaw-tools.plugin-context.ts`） |
| 冲突需重做 | **21** | 002 / 007 / 02-07 / 09 / 11 / 14 / 15 / 20-23 / 25 / 26 / 29-31 |
| 硬失败 | **9** | **全部是 `del-*` 删除型**（删除 patch 要求目标文件字节级一致） |

合计 **3777 / 4240 行 patch 需要重做** `[A]`。

结构性结论：

- **9 个删除型全挂是机制问题，不是语义问题** → 建议把"删除"改成一份 rm 清单（如 `delete.txt`，由 `apply-addons.sh` 执行），以后对上游漂移永久免疫。
- **最贵的是 browser 家族**：上游 `extensions/browser` 新增 263 / 修改 286 / 删除 18 文件（该三项计数于 `[B]` 复算一致，合计 567 = `git diff --shortstat` 的 files changed）。`browser-tool.ts` 被拆成 `browser-tool-dispatch/routing/lifecycle/screenshot/snapshot/session-tabs/binding/description` 等模块 → `05`（camoufox target + default + adapter 早返回，214 行）要按新布局重做，`03/02/04` 跟着改。
- **patch 面还变大了**：5 个新文件引用 sandbox browser bridge（`browser-tool.routing.ts`、`browser-tool.lifecycle.ts`、`attached-browser-tool-runtime.ts`、`src/agents/sandbox/config.ts`、`src/commands/doctor-sandbox.ts`），都不在现有 37 个 patch 覆盖范围内 `[A]`；`[B]` 另测得 `extensions/browser/src` 内引用 sandbox 的非测试文件 **14 → 22**。
- `002`（`OPENCLAW_DISABLE_WEB_SEARCH`）和 `007`（system-prompt 引导优先用 camoufox-cli）在 9.3 原生**仍然没有**，需求还在，只是文件漂移；都是一二十行，重做很便宜 `[A]`。

### 3.1 逐 patch 目标文件漂移量 `[B]`

`git diff --numstat v2026.7.1-2 v2026.9.3 -- <目标文件>`：

| patch | 目标文件 | 漂移 | 备注 |
|---|---|---|---|
| 01 | `docs/tools/browser.md` | +263 −81 | 章节结构基本保留（见 §7.6） |
| 02 | `extensions/browser/plugin-registration.ts` | +155 −49 | |
| 03 | `extensions/browser/src/browser-tool.schema.ts` | +263 −96 | `BROWSER_TARGETS` 仍是 `sandbox\|host\|node`；新增 capability 机制可借用 |
| 04 | `extensions/browser/src/browser-tool.test.ts` | **+3505 −362** | **最贵，基本重写** |
| 05 | `extensions/browser/src/browser-tool.ts` | +261 −909 | 1087 → 439 行，camoufox 分支要落到 dispatch/routing/description |
| 06 | `.../browser/bridge-server.auth.test.ts` | +108 −6 | |
| 07 | `.../browser/bridge-server.ts` | +87 −28 | |
| 08 | `.../browser/client-fetch.ts` | +164 −62 | |
| 09 | `.../browser/profile-capabilities.ts` | **+31 −1** | 几乎没动，但新增一批 `supports*` 字段 → 正好承载 camoufox 能力声明 |
| 11 | `src/agents/agent-tools.ts` | +614 −693 | |
| 12 | `src/agents/openclaw-tools.plugin-context.test.ts` | +93 −110 | |
| 13 | `src/agents/openclaw-tools.plugin-context.ts` | +31 −6 | `--3way` 可兜 |
| 14 | `src/agents/openclaw-tools.ts` | +364 −310 | |
| 15 | `src/agents/sandbox.ts` | +5 −23 | |
| 20 | `src/agents/sandbox/context.ts` | +149 −44 | |
| 21 | `src/agents/sandbox/docker-backend.ts` | +230 −57 | |
| 22 | `src/agents/sandbox/manage.test.ts` | +72 −6 | |
| 23 | `src/agents/sandbox/manage.ts` | +10 −11 | |
| 25 | `src/agents/sandbox/prune.test.ts` | +84 −7 | |
| 26 | `src/agents/sandbox/prune.ts` | +14 −13 | |
| 27 | `src/cli/sandbox-cli.ts` | +3 −6 | |
| 29 | `src/commands/sandbox-display.ts` | +44 −67 | |
| 30 | `src/commands/sandbox.test.ts` | +19 −6 | |
| 31 | `src/commands/sandbox.ts` | +7 −5 | |
| 34 | `src/plugins/tool-types.ts` | +22 −0 | |

### 3.2 9 个 `del-*` 目标文件在 9.3 的状态 `[B]`

**全部仍然存在，且都漂移了** → 这就是"9 个硬失败"的根因：

| del patch 目标 | 漂移 |
|---|---|
| `extensions/browser/src/browser/routes/agent.snapshot.local-managed.test.ts` | +317 −15 |
| `src/agents/sandbox/browser.create.test.ts` | +523 −152 |
| `src/agents/sandbox/browser.ts` | +104 −53 |
| `src/plugin-sdk/browser-bridge.test.ts` | +115 −41 |
| `src/agents/sandbox/browser-bridges.ts` | +33 −9 |
| `src/agents/sandbox/novnc-auth.ts` | +16 −44 |
| `src/plugin-sdk/browser-bridge.ts` | +6 −6 |
| `src/agents/sandbox/browser.novnc-url.test.ts` | +0 −6 |
| `src/security/audit-sandbox-browser.test.ts` | +0 −0 |
| `src/commands/doctor.warns-per-agent-sandbox-docker-browser-prune.e2e.test.ts` | +2 −2 |

> 结论：**9.3 没有放弃 sandbox browser / noVNC**（配置面 `agents.defaults.sandbox.browser.*`、专用 docker 网络 `openclaw-sandbox-browser`、`enableNoVnc`/`noVncEnabled` 全在，见 `src/config/types.sandbox.ts:71-94` `[B]`）。我们"删 sandbox 整条路"的 pivot 目标与上游方向相反，删除面只会越来越大。

---

## 4. awada 插件破坏面 `[A]`（生产链路，优先级最高）

- 9.3 **删掉了 `src/plugin-sdk/index.ts`**，`openclaw/plugin-sdk` 裸导入从 `exports` 消失 → awada **8 处 import** 会 `ERR_PACKAGE_PATH_NOT_EXPORTED`，**channel 加载即死**。
- `ClawdbotConfig` 在 9.3 全仓 **0 命中**（已改名 `OpenClawConfig`）→ awada **7 个文件**要改。
- 其余符号都还在：`DEFAULT_ACCOUNT_ID` / `ChannelPlugin` / `PluginRuntime` / `createTopLevelChannelDmPolicy` / `jsonResult` / `readStringParam` / `ChannelMessageActionAdapter` / `BaseProbeResult` / `RuntimeEnv` / `AgentToolResult`；adapter 的 `plugin-sdk/agent-core` 导入方式与上游一致，不用改。
- 契约文件漂移量：`channels/plugins/types.core.ts` ±228、`plugins/plugin-api.types.ts` +476、`plugin-sdk/core.ts` ±101。
- `[B]` 补充：`src/agents/sandbox` + `src/plugin-sdk` 两目录合计 **742 files changed, +56,738 / −21,580**；plugin-sdk 侧 **删除** `browser-host-inspection.ts`、`browser-node-host.ts`，**新增**导出子路径 `./plugin-sdk/browser-cdp`。

---

## 5. 工具链与治理门槛

### 5.1 工具链 `[A][B]`

- Node：9.3 要 **≥24.16.0（或 ≥26.1.0）** `[B]`；上游明确 Node 22/25/更早 24.x 有 **SQLite 文本截断**（数据损坏级）`[A]`。
- 我们 `build-dist.yml` 锁 **`24.15.0`**，共 5 处：`44`（build env）、`152-155`（linux-x64 / mac-arm64 / mac-x64 / win-x64 portable tarball）`[B]`；`ci.yml:31` 用浮动 `'24'` `[B]`。本机 node 当时为 `v24.16.0`，刚过线零余量 `[A]`。
- pnpm `packageManager` **11.2.2 → 12.3.4** `[B]`，CI 里 bundle 的 standalone pnpm 要跟着换（`lockfileVersion` 仍是 9.0）`[A]`。
- Docker 基础镜像用浮动 `node:24-bookworm`，建议钉死 `[A]`。
- **注意**：Node 抬版这条**与 openclaw 版本无关**——只要把分发的 portable Node 抬到 ≥24.16 就拿到 SQLite 截断防护，留在 7.1-2 也该做。

### 5.2 配置 / 治理 `[A]`

- **Skill Workshop 默认 `autonomous.mode="auto"` + `approvalPolicy="auto"`**（自动抓经验并自动落地技能）→ 与我们"仓是唯一真源 + 专家包按需加载"直接冲突，必须在 `config-templates/openclaw.json` 显式关掉。
- 9.3 把 Workshop 技能改成 **agent-owned collection** 并 **retire `allowSymlinkTargetWrites`** → `skill-wrappers.sh` 的软链方案要复验。
- skills 源码从 `src/agents/skills/` 搬到 **`src/skills/`** → 仓根 `AGENTS.md` 里引的 `frontmatter.ts` / `config-eval.ts:124` 路径要更新。
- 专家包依赖的"扫到 SKILL.md 停止下钻"在 9.3 **仍成立**（`MAX_GROUPED_SKILL_SCAN_DEPTH=6`，depth>0 命中 SKILL.md 即停），但建议实测一次。
- `plugins.entries.phone-control` 上游已 retire（doctor 会清）；OpenProse 移除（我们没用）；8.1 的 `codex/*`→`openai/*` 路由迁移与 `modelPolicy.allow` 与我们模板无关。

---

## 6. 用户诉求 ↔ 版本归属（关键判定）`[A]`

诉求（用户 2026-09-10 原话归纳）：①可以直接搜索本机已安装的 codex / claude code 作为 provider，onboard 流程简化；②更低的对话 token 消耗（社区用户诟病最大）。

**核查做了三层**（commit 列表 / PR 号 `git log --grep` / 文件存在性 `ls-tree`），结论一致：**两个都不在 ES 7.33 上**。

- ES 7.33 相对 7.1-2 只有 **38 个 commit**：1 个 `chore: prepare extended-stable 2026.7.33 (#133000)` + 37 个维护（deps advisory pin、上游自己的 npm/docker 打包、plugin 依赖扫描与 scaffold 校验、codex managed runtime → 0.153.4、Telegram workspace media、openshell / opencode-go 稳定性、tlon SSE 超时、release/QA）。**没有一个是 onboarding 或 token/compaction 功能**。改动构成：967 文件里 271 个是新测试、138 个是 package.json/lock pin。
- PR 号级核查（在 ES 分支逐个 `git log --grep`，全部 0 命中）：
  - 能力①：#126515 #108977 #107086 #137550 #137561
  - 能力②：#123402 #123622 #130993 #131977 #133094 #123737 #127110 #133912 #134259 #134987 #127506 #140449 #140730 #140799 #140840 #141141 #140566 #140651 #140698 #140713 #140744 #140797
- 文件级证据：
  - 能力①落地文件只在 9.x 出现：`src/wizard/setup.inference-verification.ts`、`setup.memory-import.ts`、`setup.app-recommendations.ts`、`plugin-capability-consent.ts`、`setup.default-agent.ts`，外加整套新增的 `src/commands/onboard-non-interactive/`。7.1-2 与 ES 7.33 **都没有这些文件**；两版 `src/wizard/setup.ts` 里 `claude` / `codex` 关键字命中 **0 次**。7.1 只有 `agent-auth-discovery*.ts` 那一层（给 `openclaw attach` / catalog 会话用，不是"装完直接识别本机 Codex/Claude 登录开聊"）。
  - 能力②：`src/context-engine/` 文件数 7.1-2 = **13**、ES 7.33 = **13**、9.3 = **18**（新增 `compaction-watchdog.ts`、`context-engine-abort.ts`、registry runtime adoption、host-param projection）。ES 7.33 里唯一沾 "token" 字样的改动是 `src/auto-reply/tokens.ts`——是**模型控制 token（sentinel）剥离正则**的文本保真修复，与对话 token 消耗无关；`post-compaction-context.ts` 那处是 UTF-16 安全截断。

### 6.1 两项能力的版本归属 `[A]`

| 能力 | 打底 | 真正兑现 |
|---|---|---|
| ①发现本机 Codex/Claude Code + onboarding 简化 | 8.1（Import from another agent #126515、记忆导入检测 #108977、native catalog terminals #107086） | **9.1**：quick-start lane 检测已有 Claude Code/Codex 登录与 API key 并 live 校验；Model Setup 区分 account vs API-key 并显示运行时上报邮箱；catalog "+" 直接开原生 CLI；claude-cli 走 PATH shim / Windows PATHEXT。9.2 再补 account discovery |
| ②更低对话 token 消耗 | 8.1（Anthropic 服务端 compaction #123402、xAI #123622、compaction 三修 #130993/#131977/#133094）→ 8.2（停止 byte-triggered 重复 compaction #123737/#127110/#133912/#134259）→ 9.2（被丢弃 tool result 的 token 计入 #134987） | **9.3 是大头**：prompt cache continuity 一整串（#140566/#140651/#140698/#140713/#140744/#140797/#140799）、compaction 按完整 pending request 定尺寸（#127506）、长对话与 retained memory（#136293/#139074…） |

→ **能力① 最低要 9.1，能力② 要拿满得 9.3。**

> **2026-09-11 复核更正**：上表 ② 的原始清单里混进了两个**与对话 token 无关**的 PR，已剔除 —— `#140449` 实为 `improve: retain current worker builds between sessions`（云 worker 构建复用，我们不用 worker），`#140730` 实为 `fix(memory): avoid repeated vector search startup delays`（记忆向量检索**启动延迟**，且我们模板 `agents.defaults.memorySearch.provider = none` 本来就没开）`[B]`。剔除后，② 对我们**真正可能有效**的只剩两类：compaction 决策类、provider prompt-cache 类；后者的有效性还取决于百炼端点是否实现缓存语义（见 §6.5-4）。

### 6.2 两个"升了也不会自动兑现"的前置判断 `[A]`

1. **能力① 是 onboarding 期能力**，而社区用户走的是我们的 `install.sh` + 预置 `config-templates/openclaw.json`（provider 写死 `bailian-token-plan`），**根本不进上游 wizard**。要兑现只有两条路：让 `install.sh` 把首启 onboarding 交回上游（我们只注入 skills/plugins/awada），或自己做一个"检测本机 codex/claude 登录"的脚本/skill。**这是产品决策，升级本身带不来。**
2. **能力② 的收益要拆三类**：
   - prompt cache continuity → 只有 provider 有缓存语义才省钱（Anthropic 直连 / Gemini / Bedrock / Responses 覆盖）。我们主力是百炼网关：`api: "anthropic-messages"` 路由大概率吃得到，纯 openai-compat 自定义网关未必 → **迁移前应在 9.3 上用百炼路由实测一次 usage 里的 cached token 字段**，不要假设。
   - compaction 类修复（少重复塞历史）→ **对无缓存的 GLM/DeepSeek 也直接生效**，这是最普适的真降 token，也最可能对上社区诟病。
   - 9.2/9.3 的长对话优化 → 降 CPU/延迟，**不降 token**，别算进收益。

### 6.3 不升级也能立刻做的一档 `[A]`

`skills.limits.maxSkillsInPrompt` / `maxSkillsPromptChars` / `maxSkillsLoadedPerSource` / `maxSkillFileBytes` 在 **7.1-2 就有**（`src/config/types.skills.ts:50-56`，字段与 9.3 完全一致），但我们模板里 `skills` 只写了 `entries`、**没设 limits**（`[B]` 复核 `config-templates/openclaw.json` 确认：`skills` 只有 `entries`，`agents.defaults` 只有 model / imageModel / memorySearch / models / compaction / thinkingDefault / maxConcurrent / subagents）。`agents.defaults.contextInjection` 同理可用。→ 建议先量一版"单轮 token 构成"（system prompt / 技能块 / bootstrap 文件 / 历史），再定升级优先级。

### 6.5 「升 ES 7.33 + 单独 cherry-pick 9.3 省 token 的 commit」可行性实测 `[B]`

> 2026-09-11 针对该提议做的专项实测。结论：**升 ES 7.33 可行且便宜；cherry-pick 不可行**。

**(1) 省 token 不是一个 commit，是一条压在结构重写上的链**

| 口径（`origin/extended-stable/2026.7.33..v2026.9.3`） | 实测值 |
|---|---|
| 动过 `src/context-engine` 的 commit 数 | **39** |
| `src/context-engine` 目录 diff | **15 files, +2,620 / −1,773** |
| 该目录文件数 7.1-2 / ES 7.33 / 9.3 | 13 / 13 / **18** |
| 全仓 commit 主题含 `compaction` 的数量 | **332** |
| 同期 `src/agents` 全目录 commit 数 | 3,997 |

`src/context-engine` 那 39 个 commit 里包含多个**结构性重写**，省 token 的修复就长在它们之上：`refactor: flip sessions and transcripts to sqlite storage (#98236)`、`refactor(sessions): remove file-era transcript runtime (#113233)`、`refactor(agents): consolidate compaction and context-engine ownership (#117482)`、`refactor(agents): consolidate context budgets and compaction recovery (#117149)`、`refactor: replace context-engine retry proxy with declared params (#115872)`。

**(2) cherry-pick 实测：5 个代表性 commit 全部失败**

在 `/tmp/es733b`（ES 7.33 detached worktree，tip `f619d7a9fa3`）上逐个 `git cherry-pick -n`：

| commit | 主题 | rc | 冲突文件 / 涉及文件 |
|---|---|---|---|
| `28f5f63ea42` | fix(agents): preserve prompt-cache prefix under aggregate truncation (#132017) | 1 | 4 / 6 |
| `110a636dd16` | fix(agents): preserve Responses cache prefixes across user turns (#140849) | 1 | 7 / 10 |
| `8e3f572ffa2` | fix(openai): honor native prompt cache settings (#140853) | 1 | 19 / 29 |
| `f0cc57d6b46` | fix(agents): preserve cached history when background work changes (#140799) | 1 | 32 / 52 |
| `60adac1aff6` | fix(agents): fit compacted context and prioritize foreground replies (#139822) | 1 | **91 / 129** |

合计 **153 个冲突文件次**。这不是 cherry-pick，是 re-port；而且 re-port 的是**对话装配路径**——它出 bug 的表现是"回复停在工具输出 / 历史被静默截断 / 人格漂移"，不是崩溃，很难被测出来（正是我们历史上 AtomCode 卡 busy、awada 回复丢失那一类故障的邻区）。

**(3) 更反直觉的发现：9.3 把 token 调优旋钮收走了**

`src/config/types.agent-defaults.ts` 中，7.1-2 有而 **9.3 已删除**的字段（逐个 grep 计数 7.1-2=有 / 9.3=0）：

| 字段 | 作用 | 7.1-2 | 9.3 |
|---|---|---|---|
| `compaction.maxHistoryShare` | 历史占上下文窗口比例上限（0.1–0.9，默认 0.5） | ✅ | **删除** |
| `compaction.reserveTokens` / `reserveTokensFloor` | 压缩预留 token 与下限 | ✅ | **删除** |
| `compaction.customInstructions` | 压缩摘要附加指令（保语言/人格连续性） | ✅ | **删除** |
| `contextPruning.keepLastAssistants` | 保护最近 N 个 assistant 轮不被裁剪 | ✅ | **删除** |
| `contextPruning.softTrimRatio` / `hardClearRatio` | 软裁剪 / 硬清除的上下文压力阈值 | ✅ | **删除** |
| `contextPruning.minPrunableToolChars` | 工具结果达到多少字符才值得裁 | ✅ | **删除** |

9.3 侧只新增 `compaction.enabled`、`compaction.thinkingLevel`，并把 `contextPruning` 简化成 `mode` / `ttl` / `tools` / `hardClear`。`AgentCompactionMode` 两版都是 `"default" | "safeguard"`（未变）。

→ **含义**：9.3 的 token 收益来自内部行为（缓存连续性、压缩决策），但**运维侧可调粒度变粗**。对我们这种"要给社区分发、模型上下文各异（GLM 输入上限 196,608）、需要按部署调参"的场景，丢掉 `maxHistoryShare` / `reserveTokens` 可能是**净退化**，迁移前必须评估。

**(4) provider 匹配性：cache 类修复对我们是否有效，尚未验证**

我们模板的 provider 是 `bailian-token-plan`，`api = "anthropic-messages"`，`baseUrl = https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic` `[B]`。9.3 那批 prompt-cache 修复分别是 Anthropic CLI（#140566）、OpenAI native（#140853）、Bedrock（#140797）、Responses（#140849）路径。**百炼的 anthropic 兼容端点是否实现 `cache_control` 并在 usage 里回 `cache_read_input_tokens`，必须先实测**；若不支持，合并这批 commit 的收益为 0。

**(5) 不升级就能拿的三档（7.1-2 已支持，我们模板未开）`[B]`**

| 开关 | 上游注释原文 | 我们模板现状 |
|---|---|---|
| `agents.defaults.contextPruning` | "Opt-in: prune old tool results from the LLM context to reduce token usage" | **完全未设置** |
| `skills.limits.*`（maxSkillsInPrompt / maxSkillsPromptChars / maxSkillsLoadedPerSource / maxSkillFileBytes） | 见 §6.3 | **未设置**（`skills` 只有 `entries`） |
| `compaction.maxHistoryShare` / `keepRecentTokens` / `recentTurnsPreserve` / `model` | 历史占比、保留近期 token、逐字保留轮数、**用更便宜的模型做压缩摘要** | 只设了 `compaction.mode = "safeguard"` |

→ 建议顺序：**先量"单轮 token 构成"→ 开这三档 → 再决定是否为了 compaction 那部分整体迁 9.3**（而不是 cherry-pick）。

### 6.4 ES 7.33 作为过渡的实测支撑 `[A]`

- 37 个 patch 的目标文件 **零漂移**（`git diff` 全空）→ patch 全绿，**不需要 re-port**
- awada 依赖的契约文件 **零改动**（`plugin-sdk/index.ts`、`channels/plugins/types.core.ts`、`plugins/plugin-api.types.ts`、`plugin-sdk/core.ts`、`agent-runtime.ts` 全部 0 diff）→ **awada 不用改一行**
- `engines` 仍是 node `>=22.22.3 <23 || >=24.15.0 <25 || >=25.9.0`、`packageManager` 仍 pnpm 11.2.2 → **工具链不用抬**
- 白拿：安全 advisory pin、docker/plugin 安装修复、codex runtime 0.153.4、Responses stream 修复
- 净收益判断：对我们只剩「安全 advisory pin + 2 个 plugin 扫描修复」（其余 docker/codex/Telegram/openshell 都与我们无关——我们有自己的 Dockerfile、模板里 `plugins.entries.codex.enabled=false`、不用 Telegram）
- **未 backport 到 ES 7.33 的可靠性修复**：#133520 / #133979 / #138071 / #138519（"回复停在工具输出 / 重启后丢回复"那一类）→ 这是 9.x 迁移的触发条件之一

---

## 7. 浏览器子系统专项对比（7.1-2 → 9.3）`[B]`（除注明外全部本次实测）

### 7.1 体量

| 口径 | 7.1-2 | 9.3 |
|---|---|---|
| `extensions/browser` 全量 diff | — | **567 files, +100,528 / −23,896**（A 263 / M 286 / D 18 / R 0） |
| `extensions/browser/src` 文件数 | 338 | **526** |
| └ `src/browser/` | 251 | **415** |
| └ `src/browser/extension-relay/` | 11 | **48** |
| └ `src/browser/screencast/` | 0 | **9**（+ `routes/agent.screencast.ts`） |
| └ `src/browser/routes/` | 41 | 49 |
| └ `chrome-extension/` | 11 | **61** |
| 全仓 browser/camoufox/patchright/novnc 相关文件 | 457 | **976** |
| 工具入口 `browser-tool.ts` 行数 | **1087** | **439**（+261 −909） |
| `extensions/browser/src` 内引用 sandbox 的非测试文件 | 14 | **22** |
| `extensions/cua-computer` 文件数 | **0** | **39** |
| `src/worker` 文件数 | **0** | **68** |

### 7.2 工具层：从"一个大文件"到"注册壳 + 8 个模块"

9.3 的 `browser-tool.ts` 只负责注册与编排，逻辑拆到：

| 新模块 | 职责 |
|---|---|
| `browser-tool-dispatch.ts` | action 派发（`executeBrowserTabAction`） |
| `browser-tool.routing.ts` | host / sandbox / node 目标解析、baseUrl、timeout（`resolveBrowserBaseUrl`、`resolveBrowserToolNodeTarget`） |
| `browser-tool.lifecycle.ts` | `doctor` / `status` / `start` / `stop` / `profiles` / **`importprofile`**（`:79,158-164`） |
| `browser-tool.screenshot.ts` / `.snapshot.ts` | 截图 / 快照管线 |
| `browser-tool-session-tabs.ts` | 会话 tab 注册表 |
| `browser-tool-binding.ts` | run/tab 绑定（`BROWSER_TAB_BOUND_ACTIONS`，`:49`） |
| `browser-tool-description.ts` | **按能力动态生成工具描述**（`:19-21`） |
| `attached-browser-tool-runtime.ts` | attach 到已有 CDP 端点的独立运行时（7.1-2 无此文件） |
| `browser-node-proxy/-routing/-commands/-fallback`、`browser-proxy-envelope/-upload` | node 代理链路重写 |
| `browser-runtime-state.ts`、`system-profile-api.ts` | 运行时状态 / 系统 profile 枚举 |

### 7.3 模型可见的能力变化

- **actions 19 → 24**（`browser-tool.schema.ts:32` vs 9.3 同文件）：新增 `importprofile`、`requests`、`errors`、`text`、`emulate` `[C: docs/tools/browser.md:1004,1010-1013]`
  - `text`：抽正文（首个 `selector` 命中，否则 `article`/`main`/`body`），`maxChars` 默认且上限 40,000
  - `requests` / `errors`：读网络日志 / 页面错误，支持 `filter`、`limit`（默认 50）、`clear`；页面内容与错误按**不可信外部内容**处理
  - `emulate`：`device`（Playwright 设备名）、`colorScheme`、`timezoneId`、`locale`，按此顺序应用、返回 `applied`，**非原子**
  - `importprofile`：macOS 从 Chrome/Brave/Edge/Chromium 系统 profile 导 cookie（Keychain/Touch ID 授权），仅 cookie（不含 localStorage/IndexedDB），DBSC 设备绑定会话仍可能要重登；必须跑在 browser host 上（`browser-tool.lifecycle.ts:158-164` 会抛 "system profile import must run on the browser host"）；配套 CLI `openclaw browser import-profile` / `system-profiles` / `cookie-sync`（推送到远端 Gateway 的 managed profile）`[C: docs/cli/browser.md:105-133]`
- **`navigate` 现在内联返回新页面 snapshot**（efficient interactive tier，payload 有界），批量 `act` 跨文档导航会暂停并带 `pageState` → **少一轮调用，直接省 token** `[C: docs/tools/browser.md:1014-1018; PR #114814]`
- **能力声明化**：`resolveBrowserToolCapabilities({tabBound, evaluateEnabled, profileCapabilities})` 按 profile 的 `supports*` 裁 actions，`browser-tool-description.ts` 同步改描述 → **模型看不到就不会乱调**（9.3 新机制，7.1-2 无）
- `BROWSER_TARGETS` **未变**，仍是 `["sandbox","host","node"]`（7.1-2 `schema.ts:54` / 9.3 `:63`）；profile driver 枚举仍封闭：`"openclaw" | "clawd" | "existing-session" | "extension"`（`src/config/types.browser.ts:20`）→ **没有自定义 driver 扩展点**

### 7.4 三条 7.1-2 完全没有的新链路

1. **Screencast 实时看屏**：`POST /screencast` 铸单次令牌（48 位 hex、短时效）→ WS `/browser/screencast?token=`；每 profile+tab 共享一路 CDP screencast（Chrome 推 JPEG）；不支持时回落截图并返回 `SCREENCAST_UNSUPPORTED`（`reason: existing-session | playwright | node`）`[C: docs/tools/browser-control.md:26,88-140]`。Control UI 的 Browser 面板可实时看 agent 页面、转发点击/滚轮/键盘、viewport 跟随面板尺寸 `[C: docs/web/control-ui/panels.md:83]`。7.1-2 全仓 `screencast` **0 命中**。
2. **Chrome 扩展 relay 重做**：standalone relay daemon + native-host 唤醒（**#128379**，即 8.2 的"没有 Gateway 也能控浏览器"）；`owner-*` 协议族（`owner-server/client/playwright/protocol/auth-client`）、**auth-v2**（`auth-v2-crypto.ts`、`auth-v2-websocket.ts`）、`preauth-websocket-guard.ts`（准入分区 **#134241**）、`relay-access/fetch/request/runtime/session-owner/target`；扩展侧支持每 tab 独立 copilot（#109817）、把页面/文档/选中文字一次性交给主会话（#111158）、Puppeteer 客户端接扩展 CDP（#117915）、扩展版本漂移告警（#119641）；`chrome-extension/` 从 11 → 61 文件（大量 relay/navigation/creation-lifecycle/native-cleanup/bootstrap-diagnostics 测试）。
3. **Computer Use + cloud worker 浏览器**：`extensions/cua-computer`（0 → 39 文件，含 `src/browser-actions.ts`）走**操作系统层**（截图 + 像素/辅助功能）控制配对 Mac（与显式开启的 Windows）上的 app/window，Linux 仍 experimental；`src/worker/browser-runtime.ts` 自述为 "Core-private adapter for the bundled Browser plugin's **attached** worker runtime"，提供 `createAttachedBrowserToolRuntime({cdpUrl, ensureAttachTarget, agentSessionKey, workspaceDir})` + 30s 启动超时 → worker/独立进程**不借 Gateway 凭据**即可 attach CDP 并挂出 browser 工具。

### 7.5 四个 driver 到底是什么

**先纠正**：四个名字里只有**三种真实驱动**，`clawd` 是 `openclaw` 的历史别名（clawdbot 时代遗留）。证据：

- `src/config/schema.help.runtime.ts:37`：`Per-profile browser driver mode. Use "openclaw" (or legacy "clawd") for CDP-based profiles, "existing-session" for Chrome DevTools MCP attachment, or "extension" for the authenticated Chrome extension relay.`
- `extensions/browser/src/browser/config.ts:507-509`：只有 `existing-session` / `extension` 保留原值，**其它一律归一为 `"openclaw"`**
- `extensions/browser/src/doctor-browser.ts:24`：`LEGACY_CLAWD_BROWSER_PROFILE_NAME = "clawd"`，`doctor --fix` 会归档 legacy clawd profile 残留（`:402-430`）
- `extensions/browser/src/browser/routes/basic.ts:463-467` 仍接受 `clawd`，错误文案三个并列
- `docs/tools/browser.md:347`：远端端点场景下 schema **拒绝** `openclaw` / `clawd` profile

| driver | 是什么 | 谁启动浏览器 | 传输 | 能力 |
|---|---|---|---|---|
| **`openclaw`（≡ `clawd`）** | OpenClaw 自管的隔离浏览器（内置 profile 名 `openclaw`），独立 user-data-dir | OpenClaw（或 attach 已有的） | loopback / remote **CDP** + Playwright | **最全**：per-tab WS、`/json` 端点、reset、managed tab limit、batch、pdf、download、requests/errors/text/emulate 全支持 |
| **`existing-session`** | attach 用户**真实登录的 Chrome**（内置 profile 名 `user`） | 用户的 Chrome（OpenClaw 只 attach） | **Chrome DevTools MCP** 子进程，默认 `npx -y --audit=false chrome-devtools-mcp@1.8.0 --autoConnect` | **被砍**：无 batch/pdf/download/responsebody/requests/errors/text/emulate；act 只能用 snapshot ref（CSS selector 不行，`click-coords` 例外）；click 仅左键；`type` 无 `slowly`；`wait --load networkidle` 不支持；snapshot 强制 `ai` 格式；首次 attach 有阻塞式 "Allow remote debugging?" 弹窗，**必须有人在电脑前** |
| **`extension`** | 经 OpenClaw Chrome 扩展 relay 驱动用户已登录的浏览器（内置 profile 名 `chrome`） | 用户的 Chrome | 扩展 relay（loopback 端口）+ Playwright 连 relay 端点 | 中等：`usesPersistentPlaywright=true`、`requiresCompleteTargetEnumeration=true`、`headless` 强制 false、`attachOnly=true`；**无远程调试弹窗 → 人不在电脑前也能用**（手机 Telegram/WhatsApp 场景官方推荐） |

`extension` 的端口与凭据机制（`config.ts:516-545`）：每个 extension profile 分配独立 loopback relay 端口（显式 `cdpPort` 优先，否则 `resolveExtensionRelayPorts` 自动分配，避免多 profile 抢同一端口静默失败）；内部客户端用**进程级一次性 token** 拼进 URL（`http://<EXTENSION_RELAY_CDP_USER>:<token>@127.0.0.1:<port>`），持久 relay key 只用于 HMAC 证明、**绝不进 URL 或 header**。

`existing-session` 的可定制面（`docs/tools/browser.md:862-909`）：`mcpCommand`（**任意可执行文件**，绝对路径原样解析）、`mcpArgs`（原样透传；`mcpCommand=npx` 时上游仍会前置 `-y --audit=false chrome-devtools-mcp@1.8.0`）、`userDataDir`、`cdpUrl`（`http(s)://` → `--browserUrl`，`ws(s)://` → `--wsEndpoint`；`mcpArgs` 里显式端点覆盖 `cdpUrl`；**一旦选了端点，`userDataDir` 被忽略**）。target/ref 作用域绑单个 MCP 子进程，进程重启后要重跑 `browser tabs`、重选 target、重拍 snapshot。

### 7.6 控制形态盘点：协议层还是三种，控制面多了两种

**协议/驱动层：没有第四种。** 仍是「自管 CDP / Chrome DevTools MCP / Chrome 扩展 relay」，CDP 是其中两条的共同底座（扩展 relay 本质是把 relay 端点当 CDP 端点交给 Playwright 连）。而且这三种 **7.1-2 就已全有**：两版 `docs/tools/browser.md` 大纲逐条比对，`Local vs remote control`、`Node browser proxy (zero-config default)`、`Browserless (hosted remote CDP)`、`Direct WebSocket CDP providers`（Browserbase / Notte）、`Existing session via Chrome DevTools MCP`、`Use Brave or another Chromium-based browser`、`Browser selection` 这些章节 **7.1-2 已存在**；9.3 只多了 `Browser panel in the Control UI`（:155）与 `Tab cleanup ownership`（:245）两节。

同一个 `openclaw` driver 内部的三个子形态（`docs/tools/browser.md:487-520`、`profile-capabilities.ts`）：

| 子形态 | capability mode | 判定 |
|---|---|---|
| 本地启动（自管） | `local-managed` | loopback + 非 attachOnly（`isLocalManagedProfile` = `driver==="openclaw" && cdpIsLoopback && !attachOnly`，`config.ts:227`） |
| loopback 外部 CDP + `attachOnly:true` | `local-managed`，但 `browserFilesystemLocal=false` | 例：Browserless in Docker 发布到 127.0.0.1。**不配 `attachOnly` 会被误当自管 profile** |
| 非 loopback `cdpUrl` | `remote-cdp`（`isRemote=true`、`usesPersistentPlaywright=true`） | 托管服务 Browserless / Browserbase / Notte；URL 可带 `?token=` 或 HTTP Basic，OpenClaw 在 `/json/*` 与 CDP WS 上保留凭据 |

**9.x 新增的控制面（不是新协议）**：

1. **Computer Use（`extensions/cua-computer`）** = 真正意义上的第四种形态：**不走浏览器协议，走操作系统层**（截图 + 像素/辅助功能）控制配对 Mac / 显式开启的 Windows 上的 app/window，其中包含浏览器窗口；Linux experimental。9.2 修了"CUA 窗口图里的点击/拖拽要按 OpenClaw 做的缩放换算"、"截图型 CUA 会话可暂停后看新图再继续"（`docs/releases/2026.9.2.md:2769`）。
2. **cloud worker attached browser runtime**（`src/worker/` 0 → 68 文件）。
3. **node browser proxy 重写**（形态旧、链路新）：节点靠 `caps:["browser"]` 或 `browser.proxy` 命令声明（`browser-node-commands.ts`、`browser-node-routing.ts`）；策略 `gateway.nodes.browser.mode = off|auto|manual`；新增 `browser.proxy.upload.v1`（远端上传需节点批准，未批准会给明确提示）；代理**永不**放行 `create-profile`/`delete-profile`/`reset-profile`；`nodeHost.browserProxy.allowProfiles` 是最小权限边界；动作一旦落到节点，后续 snapshot/设置就钉在该节点不再切浏览器。
4. **9.1 默认值变化（破坏性）**：standalone（`openclaw agent exec`）在没选 Gateway/node 路由时**默认用宿主机浏览器**、不需要 Gateway 凭据；依赖隐式 node 发现的要显式 `gateway.nodes.browser.mode="auto"`（`docs/releases/2026.9.1.md:1489-1493` 明说这是有意变更）。
5. **人成为共同驾驶者**：Control UI Browser 面板 + screencast（见 §7.4-1）；macOS 可把外链开成原生 WebKit tab（9.3 CHANGELOG:13,42，#140988 #141031）。
6. **sandbox Docker 浏览器依然健在**（见 §3.2 注）。

自管浏览器的二进制选择顺序（`docs/tools/browser.md:920-940`）：**Chrome → Brave → Edge → Chromium → Chrome Canary**，可用 `browser.executablePath` 覆盖；Linux 会扫 `/usr/bin`、`/snap/bin`、`/opt/google`、`/opt/brave.com`、`/usr/lib/chromium`、`/usr/lib/chromium-browser`，以及 `PLAYWRIGHT_BROWSERS_PATH` / `~/.cache/ms-playwright` 下 Playwright 托管的 Chromium。→ **"内置 Chromium" 的准确表述是"自管的 Chromium 家族浏览器"**，且**只支持 Chromium 家族**。

### 7.7 配置面破坏性变化 `[B]`

`src/config/types.browser.ts`：**14 insertions / 36 deletions**（9.3 全文仅 77 行）。

| 变化 | 内容 |
|---|---|
| **删除** | `ssrfPolicy.hostnameAllowlist`；`tabCleanup.idleMinutes` / `maxTabsPerSession` / `sweepMinutes`（只剩 `enabled`）；`actionTimeoutMs`、`localLaunchTimeoutMs`、`localCdpReadyTimeoutMs`、`remoteCdpTimeoutMs`、`remoteCdpHandshakeTimeoutMs`、`cdpPortRangeStart` |
| **新增** | `browser.allowSystemProfileImport`（默认 true，macOS）、`browser.extensionRelay.allowLegacyAuth`（默认 true）、`ssrfPolicy.blockedHostnames`（支持 `*.example.com`，**覆盖 allow**）、`ssrfPolicy.allowRfc2544BenchmarkRange`、`ssrfPolicy.allowIpv6UniqueLocalRange` |
| **改语义** | `ssrfPolicy` 变成共享类型别名 `BrowserSsrFPolicyConfig = SsrFPolicyConfig`（新文件 `src/config/types.ssrf.ts`，7.1-2 无此文件）；`color` 标 `@deprecated`（doctor-only，canonical schema 会拒）；extension driver 的 relay 端口改为每 profile 自动分配 |
| **plugin-sdk** | 新增导出子路径 `./plugin-sdk/browser-cdp`；**删除** `browser-host-inspection.ts`、`browser-node-host.ts` |

**对我们模板的影响（已核）**：

- ✅ `config-templates/openclaw.json` 与 `openclaw-awk.json` 里的 `browser` 块只有 `enabled` / `headless` / `ssrfPolicy.dangerouslyAllowPrivateNetwork: true` 三项 —— **9.3 全部仍然有效**。`navigation-guard.ts` 两版都是"只有显式 `=== false` 才拦私网"（7.1-2 `:66`、9.3 `:85`），语义未变。
- ⚠️ 若将来有人用 `browser.ssrfPolicy.hostnameAllowlist`，**9.3 会失效**（改用 `allowedHostnames` + `blockedHostnames`）。
- ⚠️ `tabCleanup` 与各类超时旋钮失去可配性 → 若线上曾靠调 `actionTimeoutMs` / `maxTabsPerSession` 解决问题，9.3 上无对应开关。

### 7.8 对 camoufox pivot 的判断

1. **camoufox 不能靠配置接进 9.3**：attach 路线是 CDP + Playwright（`cdpUrl` / `attachOnly` / `executablePath` 都只指 Chromium 家族），camoufox 是 Firefox 系**无 CDP**；driver 枚举封闭、无自定义 driver 扩展点 → pivot 的"新 target/driver + adapter"在 9.3 仍然是 patch 工程。
2. **但 9.3 让 pivot 更划算**：capability gating + description 动态生成，意味着现在 adapter 里"不支持的 action 返回错误引导 `target=host`"（`patches/browser-camoufox-pivot/README.md` 认的 R4 残留：console / dialog / `act:drag|clickCoords` / resize）可以改成 `supports*` 声明——模型根本看不到这些 action，既减少无效调用又省 token；插入点也从"改 1087 行大文件"变成"改 dispatch / routing / description 三个小模块"。
3. **9.3 浏览器新价值我们大部分吃不到**：screencast / Control UI 面板 / 扩展 relay / macOS cookie 导入 / Computer Use / cloud worker 都对着"有人在看、有 GUI、有 Mac、在云上"的场景；我们是 headless Linux 容器 + 反检测。真正有用的只有 §7.3 那三项（`navigate` 内联 snapshot、`text`/`requests`/`errors`、能力裁剪）——**全部指向省 token / 省轮次**。
4. **一条值得评估的零 patch 备选路线**：`existing-session` 的 `mcpCommand` 是"任意可执行文件"，只要求保持 Chrome MCP 的连接参数语义。理论上可写一个 **camoufox 后端的 chrome-devtools-mcp 兼容 server**，配 `driver:"existing-session"` + `mcpCommand: <我们的 bridge>`，**零 patch** 让 openclaw 驱动 camoufox。代价明确：拿不到 batch/pdf/download/requests/errors/text/emulate，act 只能用 snapshot ref，snapshot 强制 `ai` 格式，target/ref 绑子进程生命周期，且 `cdp-reachability-policy.ts:92-99` 在受管 CDP 策略下会拒带显式 `cdpUrl` 的 existing-session profile。**未验证可行性，仅列为待评估选项。**

> 单看浏览器维度：**收益 = 省 token / 省轮次；成本 = browser 家族 30 个 patch 里的重头（04 / 05 / 03 / 11 / 14 + 9 个删除型）**。只为浏览器不值；要值就得与 §6 的能力①②一起算总账。

---

## 8. 第三方 pin 与本轮已完成动作

### 8.1 pin 现状 `[A]`（版本号文件于 `[B]` 复核）

| 包 | 原 | 现（`openclaw-weixin.version.json`） | 备注 |
|---|---|---|---|
| `@tencent-weixin/openclaw-weixin` | 2.4.6 | **2.4.8** | peer `openclaw>=2026.5.12`，与 7.1-2 兼容 |
| `@wecom/wecom-openclaw-cli` | 1.1.0 | **1.1.1** | 安装流程更稳健（`plugins install` 透传 `--force`、多源 failover 不再删插件目录等） |
| `@tencent-weixin/openclaw-weixin-cli` | 2.1.4 | 2.1.4（不变） | 仍是 npm latest |
| camoufox-cli（上游） | 0.7.3 | 0.7.3 | 上游最新 = 我们 fork baseline，本轮不用跟 |

commit **`d5e112c`**（`chore(deps): bump openclaw-weixin 2.4.6 -> 2.4.8, wecom-openclaw-cli 1.1.0 -> 1.1.1`），改 5 个文件 + `CHANGELOG.md` v5.7.1 条目；`[B]` 复核已在 `origin/master` 上（当次会话内 push 两次 rc=124 失败，后续成功）。同步把 `scripts/install.sh` / `scripts/install-atomgit.sh` / `docker/docker-bootstrap.sh` 三处兜底版本 2.4.6 → 2.4.8。

### 8.2 为什么 2.4.8 在 7.1-2 上安全 `[A]`

2.4.8 的**唯一代码改动**是把 `createTypingCallbacks` 的 import 从 `openclaw/plugin-sdk/channel-runtime` 换到 `openclaw/plugin-sdk/channel-message`——那是为适配 **8.1 删掉旧子路径**。对 7.1-2 已 build 的 `dist/` 做过运行时校验：11 个 `openclaw/plugin-sdk/*` 子路径全部存在于 7.1-2 的 `package.json` exports；18 个具名导入中 12 个 value import 全命中（含关键的 `channel-message :: createTypingCallbacks`），6 个 type-only import 在 `.d.ts` 中也都在。**不验这一步，微信通道有可能加载即挂。**

### 8.3 已知坑：改了 pin，已装实例不会自动升 `[A]`

- `scripts/install.sh`：`plugins list` 里已有 openclaw-weixin 就**直接 return，不比版本**
- `scripts/update.sh`：走 `npx openclaw-weixin-cli@2.1.4 install`，该 CLI 读到 `plugins.installs[].spec` 是固定版本号时（我们正是用 `--pin` 装的）会打印「本地已安装插件为固定版本 2.4.6，跳过升级」直接 return

→ 部署/迁移时已装实例要显式跑一次：

```bash
cd openclaw && npm_config_registry=https://registry.npmmirror.com \
  pnpm openclaw plugins install @tencent-weixin/openclaw-weixin@2.4.8 --pin --force
```

wecom 那条不受影响：`install-wecom-channel.sh` 按 pin 文件 `npm pack` + sha512 校验后装，会拿到 1.1.1（需 `WISEFLOW_CONFIRM_WECOM_INSTALL=confirmed`）。

---

## 9. 当前仓库状态（2026-09-11 复验）`[B]`

| 项 | 状态 |
|---|---|
| 基座 pin | `openclaw.version` = `OPENCLAW_VERSION=2026.7.1-2` / `OPENCLAW_COMMIT=0790d9f593ad30c940ed93b5872a8cf6d6f3cf8c`，**未动** |
| `openclaw/` 工作树 | `git log -1` = `0790d9f593a`，`git describe --tags` = `v2026.7.1-2` |
| 产品版本 | 仓根 `version` = `v5.6.6`，而 `CHANGELOG.md` **没有 v5.6.6 条目**（最新是 `v5.7.1 (2026-09-10)`，其次 `v5.7.0`）。`version` 的变更历史显示它被分支来回覆盖过（`3bbe234` 把 `v5.7.0` 改回 `v5.6.6`；`fdc03d6` 曾把 `v5.6.5` 改成 `v5.6.6`）→ **既有不一致，与本轮 pin bump 无关**（`d5e112c` 只改 5 个文件，未动 `version`），但升级/发布时要一并理顺版本口径 |
| git | `master` 领先 `origin/master` **2 个 commit**（`53d4d19`、`c5b771e`，均为 DNA / expert-video 工作）；工作树有 1 个未提交修改：`crews/main/skills/published-track/SKILL.md` |
| portable Node | `.github/workflows/build-dist.yml` 仍是 `24.15.0`（行 44、152-155 共 5 处）；`ci.yml:31` 用浮动 `'24'` → **§5.1 的 Node 抬版尚未做** |
| `skills.limits` | `config-templates/openclaw.json` 里**仍未设置** → **§6.3 的零成本降 token 项尚未做** |
| 本机部署实例 | 未动（`~/.openclaw` 只读铁律） |

---

## 10. 待拍板项

| # | 决策 | 选项 | 已知成本 / 依据 |
|---|---|---|---|
| 1 | **基线选哪条** | (a) 直接迁 `2026.9.3`；(b) 先切 `extended-stable/2026.7.33`（pin `f619d7a9fa3`，或等它打 tag）过渡，再排期 9.3；(c) 暂不动；(d) **ES 7.33 + cherry-pick 9.3 省 token commit —— 已实测否决**（§6.5-2：5 个 commit 全部冲突，合计 153 个冲突文件次） | (a) 4.5–7 人日 `[A]`；(b) ≈半天，patch/awada 零漂移，但拿不到能力①② `[A]`；能力①最低 9.1、能力②要 9.3（§6.1） |
| 2 | **portable Node 抬到哪** | 24.16+ / 直接 26（上游推荐 26） | 与 openclaw 版本解耦，留 7.x 也该做（§5.1）；改 `build-dist.yml` 5 处 + `ci.yml` + Docker 基础镜像钉死 |
| 3 | **9.x 迁移的触发条件认不认** | 认 / 不认（改为现在就一次性做完） | 触发条件草案：生产出现"回复停在工具输出 / 重启后丢回复"（#133520 #133979 #138071 #138519 **均未 backport 到 ES 7.33**）；或 ES 7.33 停止提交；或需要 9.x 独有能力 |
| 4 | **`install.sh` 幂等判断要不要改** | 改成"已装版本 ≠ pin 版本 → `--force` 升级" / 维持手动补装 | 十几行，根治 §8.3 的坑 |
| 5 | **浏览器路线** | (a) 按 9.3 新模块布局重画 pivot（05/03/04/09 + `del-*` 改 rm 清单 + 补 5 个新文件）；(b) 先在 7.1-2 上把"能力裁剪"等价实现到自有 adapter 层（半天量级，不需动基座）；(c) 评估 §7.8-4 的"MCP 桥零 patch"路线 | 见 §7.8；(a) 的工时已含在 #1 的 4.5–7 人日里 |
| 6 | **是否先做"单轮 token 构成"实测 + 三档配置调参** | 做 / 不做 | 半天、立刻见效、与升级解耦（§6.3、§6.5-5：`contextPruning` / `skills.limits` / `compaction.*` 三档都是 7.1-2 已支持但我们没开）；也是判断能力② 收益基线的前置数据 |
| 7 | **是否先实测百炼端点的 prompt cache 语义** | 做 / 不做 | 决定 9.3 那批 cache 修复对我们是否有价值（§6.5-4）；不做这一步，能力② 的收益无法量化 |

---

## 附录 A：复验命令

```bash
cd /home/wukong/wiseflow/openclaw   # 上游工作树，两个 tag 都已在本地对象库

# 体量
git diff --shortstat v2026.7.1-2 v2026.9.3 -- extensions/browser
for f in A M D R; do echo -n "$f: "; git diff --name-only --diff-filter=$f v2026.7.1-2 v2026.9.3 -- extensions/browser | wc -l; done
for t in v2026.7.1-2 v2026.9.3; do echo -n "$t "; git ls-tree -r --name-only $t -- extensions/browser/src | wc -l; done
git show v2026.7.1-2:extensions/browser/src/browser-tool.ts | wc -l   # 1087
git show v2026.9.3:extensions/browser/src/browser-tool.ts  | wc -l   # 439

# 工具链
for t in v2026.7.1-2 v2026.9.3; do git show $t:package.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["version"],d["engines"],d["packageManager"].split("+")[0])'; done

# 逐 patch 目标漂移
for p in /home/wukong/wiseflow/patches/browser-camoufox-pivot/patches/*.patch; do
  f=$(grep -m1 "^+++ b/" "$p" | sed 's|^+++ b/||'); [ -z "$f" ] && f=$(grep -m1 "^--- a/" "$p" | sed 's|^--- a/||')
  printf '%-70s %s\n' "$f" "$(git diff --numstat v2026.7.1-2 v2026.9.3 -- "$f" | awk '{print "+"$1" -"$2}')"
done

# driver / 能力 / 配置面出处
git show v2026.9.3:src/config/types.browser.ts
git show v2026.9.3:src/config/types.ssrf.ts
git show v2026.9.3:extensions/browser/src/browser/profile-capabilities.ts | head -140
git show v2026.9.3:extensions/browser/src/browser/config.ts | sed -n '495,620p'
git show v2026.9.3:extensions/browser/src/browser-tool.schema.ts | sed -n '1,120p'
git show v2026.9.3:docs/tools/browser.md | sed -n '487,560p;860,950p'

# 版本线拓扑
git log --oneline -1 origin/extended-stable/2026.7.33                 # f619d7a9fa3
git rev-list --count v2026.7.1-2..origin/extended-stable/2026.7.33    # 38
git merge-base --is-ancestor v2026.7.1-2 origin/extended-stable/2026.7.33 && echo YES   # YES
git merge-base --is-ancestor v2026.7.1-2 v2026.9.3 && echo YES || echo NO               # NO
git merge-base v2026.7.1-2 v2026.9.3 | xargs git log -1 --format='%h %ad %s' --date=short
MB=$(git merge-base v2026.7.1-2 v2026.9.3)
git rev-list --count $MB..v2026.9.3      # 24853
git rev-list --count $MB..v2026.7.1-2    # 224
```

## 附录 B：关键证据指针（9.3 tag）

| 主题 | 位置 |
|---|---|
| driver 枚举 | `src/config/types.browser.ts:20` |
| driver 语义说明 | `src/config/schema.help.runtime.ts:37` |
| driver 归一化（clawd → openclaw） | `extensions/browser/src/browser/config.ts:507-509` |
| legacy clawd profile 清理 | `extensions/browser/src/doctor-browser.ts:24,402-430` |
| 远端端点拒绝 openclaw/clawd profile | `extensions/browser/src/browser/routes/basic.ts:463-467`；`docs/tools/browser.md:347` |
| extension relay 端口 / token | `extensions/browser/src/browser/config.ts:516-545` |
| existing-session 解析（MCP） | `extensions/browser/src/browser/config.ts:546-575`；`docs/tools/browser.md:752-909` |
| capability mode 判定 | `extensions/browser/src/browser/profile-capabilities.ts`（`remote-cdp` = `!cdpIsLoopback`；`local-managed.browserFilesystemLocal = !attachOnly`） |
| 工具能力裁剪 | `extensions/browser/src/browser-tool.schema.ts`（`resolveBrowserToolCapabilities`）；`browser-tool-description.ts:19-21`；`browser-tool-binding.ts:49` |
| Chrome MCP 与受管 CDP 策略冲突 | `extensions/browser/src/browser/cdp-reachability-policy.ts:92-99` |
| SSRF 生效逻辑 | `extensions/browser/src/browser/navigation-guard.ts:85`（7.1-2 为 `:66`） |
| importprofile 必须在 browser host | `extensions/browser/src/browser-tool.lifecycle.ts:158-164` |
| screencast | `docs/tools/browser-control.md:26,88-140`；`extensions/browser/src/browser/screencast/*` |
| Control UI Browser 面板 | `docs/web/control-ui/panels.md:83` |
| node proxy | `extensions/browser/src/browser-node-commands.ts`、`browser-node-routing.ts`（`gateway.nodes.browser.mode`） |
| worker attached runtime | `src/worker/browser-runtime.ts`；`extensions/browser/src/attached-browser-tool-runtime.ts` |
| 浏览器二进制选择顺序 | `docs/tools/browser.md:920-940` |
| sandbox browser / noVNC 仍在 | `src/agents/sandbox/browser.ts`、`novnc-auth.ts`、`browser-bridges.ts`、`src/plugin-sdk/browser-bridge.ts`、`src/config/types.sandbox.ts:71-94` |
| 8.1 浏览器专项 release notes | `docs/releases/2026.8.1/browser-and-computer-use.md`（401 行） |
| 9.1 host-first 默认 | `docs/releases/2026.9.1.md:1483-1493` |
| 9.2 Browser & Computer Use | `docs/releases/2026.9.2.md:2759-2771` |
| 我们的 pivot 现状 | `patches/browser-camoufox-pivot/README.md`、`patches/browser-camoufox-pivot/patches/01-35`、`patches/browser-camoufox-pivot/files/camoufox-cli.adapter.ts` |
