# IT Engineer Agent - Memory

## 关于 WiseFlow 项目(我正在维护的项目)

项目背景、功能介绍和目录结构详见工作区中的**项目背景.md**(由部署脚本自动同步,每次升级均为最新版)。

### 项目基本信息
- **项目名称**:WiseFlow
- **仓库地址**:https://github.com/TeamWiseFlow/wiseflow
- **上游 OpenClaw 仓库**:https://github.com/openclaw/openclaw
- **OpenClaw 官方教程**:https://docs.openclaw.ai/
- **历史曾用名**:openclaw_for_business、OFB(代码已合并,统一使用 WiseFlow)

---

## 安装路径(由 setup-crew.sh 自动维护)

> 实际 WiseFlow 项目路径记录在 `OFB_ENV.md`(同目录,历史命名保留),每次运行 `setup-crew.sh` 自动更新。
> 执行任何脚本前,先读取该文件确认路径,再 `cd <WISEFLOW_PROJECT_ROOT>` 后调用 `./scripts/xxx.sh`。

运行时数据位于 `~/.openclaw/`:
- `~/.openclaw/openclaw.json`:实际运行配置(勿手动大幅修改)
- `~/.openclaw/workspace-*/`:各 Agent 的工作区
- `~/.openclaw/agents/*/sessions/`:会话记录(用于用量统计)

---

## AWADA channel 启用

awada extension 是专为对外 crew（如 sales-cs）打造的消息通道，可令 sales-cs 以企业微信联系人的形态连接外部用户。配置默认直接启用 customerDB hook。

**启用/配置走 `awada-channel-setup` 技能**（SOP：装依赖 → 写 openclaw.json → 重启 Gateway → 验证）。排障检查单亦在该技能 SKILL.md 内。

> awada 已拍平单层（D8），路径 = `<WISEFLOW_PROJECT_ROOT>/awada/`（非 `awada/awada-extension/`）。

---

## LLM 模型参数约束(火山方舟 awk provider)

### GLM 5.2 系列(模型 id `glm-latest` / 其他 GLM 5.2 变体)

- **Provider 端点**:`https://ark.cn-beijing.volces.com/api/coding/v3`(provider alias `awk`)
- **实际 max_tokens 上限**:**128000**
- **模型卡 / 官方文档标的**:131072(**这是 GLM 模型本身的能力上限**,但火山方舟 `coding/v3` 端点把它截到 128000)
- **错误症状**:所有请求 `400 The parameter 'max_tokens' specified in the request are not valid: integer above maximum value, expected a value <= 128000, but got 131072 instead`
- **openclaw.json 正确配置**:`maxTokens: 128000`

### 排查清单:某个 agent 全报 "Something went wrong"

1. **看 gateway-error.log**(`/home/wukong/wiseflow-pro/logs/gateway-error.log`),找 `embedded run agent end: isError=true` + 紧跟的 `error=LLM request failed` 行。
2. **看 sessions.json 里那个 agent 的 modelOverride**(`~/.openclaw/agents/<agent>/sessions/sessions.json`,key 是 `agent:<agent>:feishu:direct:<user_ouid>`):
   - 如果有 `modelOverride` + `modelOverrideSource: "user"` → 说明之前 `/model <xx>` 把会话锁死在那个模型上了。
   - **修复**:用户在该 agent 对话里发 `/model <默认主模型>`,或 IT Engineer 删掉 sessions.json 里的 `modelOverride/providerOverride/modelOverrideSource` 三个字段(注意先 `cp` 备份 `.bak-<日期>`)。
   - **原因**:用户用 `/model` 切换是持久化的,`/new` 不会清。
3. **如果错误是 `max_tokens` 超过 provider 上限**:改 `openclaw.json` 里那个模型的 `maxTokens`。注意备份,hot-reload 通常生效。

---

## ⚠️ 重大警告：`pnpm openclaw <subcommand>` 会触发 build，在运行中的 Gateway 上使用会掏空系统

**防范规则（勿犯）**：

1. **永远不要在生产 Gateway 运行中调用 `pnpm openclaw <任何子命令>`**，包括看起来“只读”的 `cron list`、`cron show`、`cron runs`、`config get` 等。只要走 `pnpm openclaw` 入口，都会触发 build。
2. **查询/操作 cron、config、会话状态、系统状态都走 MCP 工具**：
   - cron 查询/增删改 → `cron` MCP 工具（不触发 build，不写 dist）
   - config 查询/修改 → `gateway` MCP 工具的 `config.get` / `config.patch` / `config.apply`
   - 会话状态 → `sessions_list` / `sessions_history` / `session_status`
3. **如果实在需要走 CLI**：优先看项目里的 `dist/` 是否已 build 过且是热的，可以直接 `node dist/index.js <subcommand>` 跳过 npm script 的 build wrapper；但在生产上也不推荐。
4. **对话里跟用户呈现任何 cron/config 信息**：走 MCP 工具拿到结果。

**反例（禁止）**：
```bash
cd /home/wukong/wiseflow-pro/openclaw && pnpm openclaw cron list
cd /home/wukong/wiseflow-pro/openclaw && pnpm openclaw config get
cd /home/wukong/wiseflow-pro/openclaw && pnpm openclaw doctor --fix
# 以上三条都会触发 build，都是雷区。
```

**正例（推荐）**：
```
MCP cron 工具调用，action="list" / "get" / "add" / "update" / "remove" / "run" / "runs"
MCP gateway 工具调用，action="config.get" / "config.patch" / "config.apply" / "restart"
```

| 需求 | 工具 |
|------|------|
| cron 查询 / 增删改 / 运行历史 / 手动触发 | `cron` MCP 工具 |
| config 查询 / 修改 / 应用 / 重启 Gateway | `gateway` MCP 工具 |
| 会话 查询 / 历史 / 状态 / 送信 / spawn | `sessions_list` / `sessions_history` / `session_status` / `sessions_send` / `sessions_spawn` |
| 节点 / 文件传输 / 调用 | `nodes` / `file_fetch` / `file_write` / `dir_list` / `dir_fetch` |
| 技能架库 增删改查 | `skill_workshop` |

---

## ⚠️ OpenClaw binding routing 的关键坑

**坑 1：binding 不写 `accountId` 时不会"通配所有 account"** — `src/routing/resolve-route.ts` 里的 `normalizeBindingMatch` 把没填的 `match.accountId` 视为 `""`（`DEFAULT_ACCOUNT_ID` = `"default"`），路由查找时只匹配 `accountId="default"` 的请求。**没有匹配的 binding 时回退到 `resolveDefaultAgentId` = default agent（main）**，看起来 binding 写了但消息还是去 default agent。

**正确做法**（任何 binding 改 channel 路由都要写 `accountId`）：
- 想通配所有 account：用 `"accountId": "*"`（会进 `byAnyAccount` 桶）
- 想精确匹配某个 account：用具体 account id

**坑 2：routing 缓存 `resolvedRouteCacheByCfg` 不会因 SIGUSR1 hot-reload 重置** — 它是 `WeakMap<OpenClawConfig, ...>`，基于 cfg 对象引用判断，hot-reload 不换 cfg 引用所以不重置。改 binding 后必须用 `systemctl --user restart openclaw-gateway.service` 完整重启（这会断所有 session，因此执行前必须告知用户并征得同意）。

**坑 3：sessions.json 中的旧 session entry 会"劫持"新消息** — openclaw 看到有 `(channel, peer) → sessionId` 的 entry 直接复用，agent 也按 entry 里绑的来，跟 binding 无关。改 binding 之前/之后都要查 `agents/<agent>/sessions/sessions.json` 把这个 entry 删掉，否则即使 binding 改对了，session 缓存仍把消息路由回旧 agent。

## 定时任务(Cron)维护方案

> **v2026.6.6 起**:cron 存储已从 JSON 文件迁移至 SQLite,**禁止再编辑任何 JSON 文件**。

### 存储变更

| 项目 | 旧方案(已废弃) | 新方案(当前) |
|------|------------------|----------------|
| Job 定义 | `~/.openclaw/cron/jobs.json` | SQLite 表 `cron_jobs` |
| 运行时状态 | `~/.openclaw/cron/jobs-state.json` | SQLite 同表内字段 |
| 运行日志 | `~/.openclaw/cron/runs/*.jsonl` | SQLite 表 `cron_run_logs` |
| 数据库位置 | - | `~/.openclaw/state/openclaw.sqlite` |

旧文件已被 `doctor --fix`（上游升级后一次性迁移，由用户手动调用）重命名为 `.migrated` 后缀,数据已导入 SQLite。`.migrated` 文件可安全删除。

> ⚠️ **生产 Gateway 运行中，不得调用 `pnpm openclaw cron ...` / `node dist/index.js cron ...` 任何 CLI 入口**。它会触发重新 build 并写运行中 Gateway 共享的 `dist/`，多次连续调用可能导致系统崩溃。一律走 MCP `cron` 工具。

**正确姿势（MCP `cron` 工具，零 build、零 dist 写入）**：

```
# 查看所有定时任务
cron(action="list")

# 查看某个任务详情
cron(action="get", jobId="<job-id>")

# 新增定时任务（完整 schema 见工具描述：schedule 、payload、delivery、sessionTarget 等）
cron(action="add", job={
  "name": "任务名",
  "agentId": "<agent-id>",
  "schedule": {"kind": "cron", "expr": "0 8 * * *", "tz": "Asia/Shanghai"},
  "payload": {"kind": "agentTurn", "message": "任务描述"},
  "sessionTarget": "isolated",
  "delivery": {"mode": "announce", "channel": "feishu", "to": "user:ou_xxx"}
})

# 启用 / 禁用
cron(action="update", jobId="<job-id>", patch={"enabled": true})
cron(action="update", jobId="<job-id>", patch={"enabled": false})

# 修改投递目标
cron(action="update", jobId="<job-id>", patch={
  "delivery": {"mode": "announce", "channel": "feishu", "to": "user:ou_xxx"}
})

# 修改模型覆盖
cron(action="update", jobId="<job-id>", patch={
  "payload": {"model": "provider/model"}
})

# 删除任务
cron(action="remove", jobId="<job-id>")

# 手动触发一次（默认仅在到期时走，加 runMode="force" 立刻触发）
cron(action="run", jobId="<job-id>", runMode="force")

# 查看运行历史
cron(action="runs", jobId="<job-id>", limit=20)
```

### 直接查询 SQLite（只读排查用）

SQLite 只读查询不会触发 build，安全。但 **不得直接 UPDATE/INSERT/DELETE `cron_jobs` 表**，会跟 MCP 的状态机、`job_json` 冲突。

```bash
# 列出所有 job 及关键字段
sqlite3 ~/.openclaw/state/openclaw.sqlite \
  "SELECT job_id, name, schedule_expr, enabled, delivery_mode, delivery_channel, delivery_to FROM cron_jobs;"

# 查看最近运行记录
sqlite3 ~/.openclaw/state/openclaw.sqlite \
  "SELECT job_id, seq, datetime(ts/1000, 'unixepoch', 'localtime') as time, status, error FROM cron_run_logs ORDER BY ts DESC LIMIT 20;"
```

修改、增删都走 MCP `cron` 工具，**不允许手工 SQL 修改这些表**。

### 迁移操作（如需要）

1. 读取`~/.openclaw/cron/job.json` 文件，获取目前的定时任务配置。
2. 按上使用`cron`MCP工具进行配置。

### 重要提醒

1. **禁止手动编辑** `~/.openclaw/cron/` 下的任何 JSON 文件,它们已不再被运行时读取
2. **禁止手动 UPDATE/INSERT/DELETE** SQLite 中 `cron_jobs` / `cron_run_logs` 表；必须走 MCP `cron` 工具，CLI 会同时更新结构化列和概念上的 `job_json` 快照
3. cron 运行在 Gateway 进程内,修改后立即生效,无需重启

---

## crew权限（`exec-approvals.json` + `ALLOWED_COMMANDS`）维护经验

### 文件职责
- **`~/.openclaw/exec-approvals.json`** — 运行时实际生效的白名单。每条 entry：`{ id, pattern, lastUsedAt?, lastUsedCommand?, lastResolvedPath? }`。Gateway 在每次 exec 调用时读它并写回 `lastUsedAt`（活跃更新，不需重启）。`security: "allowlist"` 的 agent 没命中即返回 `exec denied: allowlist miss`。
- **`~/.openclaw/workspace-<agent>/ALLOWED_COMMANDS`** — **真正的 source of truth**。`setup-crew.sh` 读它 + SOUL.md 的 `command-tier:`（T0/T1/T2/T3）→ 重新生成 `exec-approvals.json`。每行 `+命令` / `-命令` 形式，注释以 `#` 起头。

### 流程：新增全局放行命令
1. **备份**：`cp ~/.openclaw/exec-approvals.json{,.bak-$(date +%Y%m%d-%H%M%S)}` 和 `cp workspace-*/ALLOWED_COMMANDS{,.bak-...}`（仅备份被改的那个 agent）。
2. **改 `exec-approvals.json`**：往每个 `security: "allowlist"` agent 的 `allowlist` 数组里 push 三条 `{ id: <uuid>, pattern: "/usr/bin/<bin>", lastUsedAt: <ms>, lastUsedCommand: "IT-ENGINEER PRE-APPROVED YYYY-MM-DD: <bin>", lastResolvedPath: "/usr/bin/<bin>" }`。**不要给 `it-engineer` 加**（它是 T3 full）。**用 atomic write**（temp + `os.replace`），因为 gateway 在并发写回 `lastUsedAt`。
3. **改对应 agent 的 `ALLOWED_COMMANDS`**：尾部追加 `# 注释行` + 三行 `+pdfimages` / `+pdftoppm` / `+pdftocairo`。setup-crew.sh 会把 basename 经 `which`/`readlink -f` 解析成绝对路径写进 exec-approvals.json，下次跑不会被覆盖掉。
4. **不要重启 gateway**。gateway 进程读 `exec-approvals.json` 是 live 的，只要新条目在文件里，下次 exec 就走新条目。重启是过度反应。
5. **不要跑 setup-crew.sh**。如果将来真要重生成，等用户手动跑。

### 验证命令
```bash
# 1) 查某个 agent 有没有某 pattern
python3 -c "
import json
d=json.load(open('/home/wukong/.openclaw/exec-approvals.json'))
for e in d['agents']['<agent>']['allowlist']:
    if 'pdfimages' in e['pattern']: print(e)
"
```
