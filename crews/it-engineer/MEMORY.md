# IT Engineer Agent - Memory

## 内置运维知识

### 权限策略

- **内 crew（main / content-producer / it-engineer）**：`crew-type: internal` → `exec-approvals.json` 给 `security: full`（无白名单）。
- **对外 crew（sales-cs）**：`crew-type: external` + 显式 `ALLOWED_COMMANDS` `+` 条目 → `security: allowlist`（只放行声明脚本，prompt injection 防线）；无 `+` 条目的对外 crew → `deny`。

### skill 依赖策略

#### 镜像预装常用包

内置技能所需依赖已经在部署环境中。

#### volume 扩展

- 用户额外装 skill 时的依赖路径：
  - **Python**：`pip install --target ~/.openclaw/skills/<skill>/vendor/ <pkg>`（PYTHONPATH 由 `docker-entrypoint.sh` 注入）
  - **Node**：`cd ~/.openclaw/skills/<skill> && npm install <pkg>`（局部 `node_modules`）
- 重启不丢（volume 持久化）

#### 依赖安装规范

- **何时装**：
  - skill 报错 `ModuleNotFoundError: No module named 'xxx'` → 装 xxx 到该 skill 的 vendor
  - skill 报错 `Cannot find module 'xxx'`（Node）→ 装 xxx 到该 skill 局部 node_modules
- **何时不装**：
  - skill 内 import 但镜像已预装 → 检查 image 是否完整 / 用户是否漏装
  - 通用依赖（如 requests、Pillow）应已在镜像，不需用户装
- **依赖冲突处理**：
  - **Python**：vendor 目录是隔离的（每个 skill 独立），不冲突；跨 skill 同名不同版本需求 → 各自装各自的 vendor
  - **Node**：局部 node_modules 可能与全局 openclaw 依赖冲突 → 用 `npm install --save-prefix=~` 避免锁到特定 patch 版本
- **it-engineer 介入**：
  - 用户报告"skill 不能用" → 1）查 `~/.openclaw/logs/gateway-error.log` 2）确认 `pip list --target ~/.openclaw/skills/<skill>/vendor/` 或 `ls ~/.openclaw/skills/<skill>/node_modules/` 3）按需装
  - **不**主动更新 skill 自带的依赖版本（避免破坏 skill 兼容性）
- **特殊场景**：
  - **镜像重建后**（用户重 deploy Docker 镜像）→ 镜像预装的包恢复；vendor 目录在 volume 持久化不受影响
  - **本机源码部署**（非 Docker）→ 直接 `pip install <pkg>` 到系统 Python 即可（无 vendor 隔离需要），或者按 volume 扩展模式到 skill 子目录

### camoufox-cli 排故

- **指纹模板 bake**（Docker 镜像内）：`/root/.openclaw/logins/_template/camoufox-cli.json`，由 `Dockerfile wiseflow-layer` 阶段跑 `camoufox-cli --session _template --persistent --headless open about:blank` 生成。
- **运行时模板复用**：每个 agent session 启动前 `cp /root/.openclaw/logins/_template/camoufox-cli.json ~/.camoufox-cli/profiles/<session>/`。
- **约束**：不 fork camoufox-cli / 不 bake chromium / 每 agent 一 session / 独立 profile dir / 独立 cookie state。
- **常见问题**：
  - `camoufox-cli open` 超时 → `camoufox-cli close --all` 清残留 + 重试
  - `cookie-import` 后访问仍 401 → cookies 过期 / 域不匹配；重新走登录流
  - daemon 残留 → `camoufox-cli close --all` 兜底；每任务结束必须 `session-cleanup`
  - **⚠️ camoufox-cli 二进制误报缺失**：`camoufox-js` 的 `camoufoxPath()` 只检查 `version.json` 不检查二进制文件本身。`camoufox-cli install` 会误报 "already up to date"。排查时必须用 `ls -la ~/.cache/camoufox/camoufox-bin` + `file` + 实际 `open` 测试确认，不要只看 install 输出。

### openclaw.json 禁止更改的项目

- **browser 模块**：本系统已对浏览器使用做过优化，默认使用 camoufox-cli，Browser tool 是托底手段（处理反爬特别严格的站点），整个 browser 部分配置已是该场景下的最佳配置。即使用户明确要求更改，也应解释理由并再三征得确认。

### ⚠️ 控制面操作铁律：走 MCP 工具，绝不走 `pnpm openclaw` CLI

生产 Gateway 运行中，**任何** `pnpm openclaw <子命令>`（包括看似只读的 `cron list` / `cron show` / `cron runs` / `config get` / `doctor --fix`）都会触发重新 build、写运行中 Gateway 共享的 `dist/`，多次连续调用可能导致系统崩溃。这是唯一硬性禁止。

**原则（一句话）**：控制面工具（`cron` / `gateway` / `nodes`）**可用就用 MCP 工具**；**不可用**（聊天渠道被 owner-only deny 移除）就**直接操作 SQLite**，不绕弯、无需征求许可。

**工具映射表**：

| 需求 | 工具 |
|------|------|
| cron 查询 / 增删改 / 运行历史 / 手动触发 | `cron` MCP 工具 |
| config 查询 / 修改 / 应用 / 重启 Gateway | `gateway` MCP 工具 |
| 会话 查询 / 历史 / 状态 / 送信 / spawn | `sessions_list` / `sessions_history` / `session_status` / `sessions_send` / `sessions_spawn` |
| 节点 / 文件传输 / 调用 | `nodes` / `file_fetch` / `file_write` / `dir_list` / `dir_fetch` |
| 技能架库 增删改查 | `skill_workshop` |

### 定时任务（Cron）维护方案

> **v2026.6.6 起**：cron 存储已从 JSON 迁移至 SQLite（`~/.openclaw/state/openclaw.sqlite`，表 `cron_jobs` / `cron_run_logs`）。**禁止编辑 `~/.openclaw/cron/` 下任何 JSON**（已废弃，运行时不再读取；旧文件已由 `doctor --fix` 迁移为 `.migrated`，可安全删除）。

**操作原则**：`cron` MCP 工具可用 → 用工具；不可用 → 直接操作 SQLite。修改即时生效（跑在 Gateway 进程内），无需重启。绝不走 `pnpm openclaw` / `node dist/index.js` CLI。

#### 方式一：MCP cron 工具（首选）

```
# 查看所有任务 / 任务详情
cron(action="list")
cron(action="get", jobId="<job-id>")

# 新增任务（完整 schema 见工具描述：schedule、payload、delivery、sessionTarget 等）
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

# 修改投递目标 / 模型覆盖
cron(action="update", jobId="<job-id>", patch={"delivery": {"mode": "announce", "channel": "feishu", "to": "user:ou_xxx"}})
cron(action="update", jobId="<job-id>", patch={"payload": {"model": "provider/model"}})

# 删除任务 / 手动触发（runMode="force" 立即触发）/ 查看运行历史
cron(action="remove", jobId="<job-id>")
cron(action="run", jobId="<job-id>", runMode="force")
cron(action="runs", jobId="<job-id>", limit=20)
```

#### 方式二：直接操作 SQLite（工具不可用时）

**通用步骤（每次修改必走）**：

1. **查**：先确认目标 job
2. **备份**：受影响行存 /tmp
3. **改**：SQL 必须**同时更新「结构化列」和「job_json 快照」**（两处不一致会打架：MCP 工具读列、运行时读 job_json）
4. **验证**：改完立刻回读，确认两处都已生效

```bash
# 1. 查
sqlite3 ~/.openclaw/state/openclaw.sqlite "SELECT job_id, name, enabled, payload_model, payload_fallbacks_json FROM cron_jobs;"

# 2. 备份
sqlite3 ~/.openclaw/state/openclaw.sqlite "SELECT job_id, name, payload_model, payload_fallbacks_json, job_json FROM cron_jobs WHERE job_id='<job-id>';" > /tmp/cron_bak_$(date +%Y%m%d-%H%M%S).txt
```

```sql
-- 3. 改（常用操作，2026-08-22 实操验证）

-- 清空 fallback（让任务继承 openclaw.json 的 agents.defaults.model）
UPDATE cron_jobs SET payload_fallbacks_json = NULL, job_json = json_remove(job_json, '$.payload.fallbacks') WHERE job_id = '<job-id>';

-- 设置 fallback
UPDATE cron_jobs SET payload_fallbacks_json = '["ark/deepseek-v4-flash"]', job_json = json_set(job_json, '$.payload.fallbacks', json('["ark/deepseek-v4-flash"]')) WHERE job_id = '<job-id>';

-- 指定任务模型
UPDATE cron_jobs SET payload_model = 'bailian/deepseek-v4-flash-0731', job_json = json_set(job_json, '$.payload.model', 'bailian/deepseek-v4-flash-0731') WHERE job_id = '<job-id>';

-- 禁用 / 启用
UPDATE cron_jobs SET enabled = 0, job_json = json_set(job_json, '$.enabled', false) WHERE job_id = '<job-id>';
```

```bash
# 4. 验证（回读确认列与 job_json 两处一致）
sqlite3 ~/.openclaw/state/openclaw.sqlite "SELECT job_id, name, enabled, payload_model, payload_fallbacks_json, job_json FROM cron_jobs WHERE job_id='<job-id>';"

# 只读排查（任何时候都安全）：列出所有 job 关键字段 / 最近运行记录
sqlite3 ~/.openclaw/state/openclaw.sqlite "SELECT job_id, name, schedule_expr, enabled, delivery_mode, delivery_channel, delivery_to FROM cron_jobs;"
sqlite3 ~/.openclaw/state/openclaw.sqlite "SELECT job_id, seq, datetime(ts/1000, 'unixepoch', 'localtime') as time, status, error FROM cron_run_logs ORDER BY ts DESC LIMIT 20;"
```

**避坑**：
- 只读 SQLite 查询任何时候都安全（不触发 build）；**修改**仅在 cron/gateway 工具不可用时才走 SQL
- 不要手工改 `cron_run_logs` 表（运行历史，只读查询可以）
- cron 修改即时生效，无需重启

### ⚠️ OpenClaw binding routing 的关键坑

**坑 1：binding 不写 `accountId` 时不会"通配所有 account"** — `src/routing/resolve-route.ts` 的 `normalizeBindingMatch` 把没填的 `match.accountId` 视为 `""`（`DEFAULT_ACCOUNT_ID` = `"default"`），路由查找只匹配 `accountId="default"` 的请求。没有匹配的 binding 时回退到 `resolveDefaultAgentId` = default agent（main），看起来 binding 写了但消息还是去 default agent。

**正确做法**（任何 binding 改 channel 路由都要写 `accountId`）：
- 想通配所有 account → `"accountId": "*"`（会进 `byAnyAccount` 桶）
- 想精确匹配某个 account → 用具体 account id

**坑 2：routing 缓存 `resolvedRouteCacheByCfg` 不会因 SIGUSR1 hot-reload 重置** — 它是 `WeakMap<OpenClawConfig, ...>`，基于 cfg 对象引用判断，hot-reload 不换 cfg 引用所以不重置。改 binding 后必须用 `systemctl --user restart openclaw-gateway.service` 完整重启（这会断所有 session，执行前必须告知用户并征得同意）。

**坑 3：sessions.json 中的旧 session entry 会"劫持"新消息** — openclaw 看到有 `(channel, peer) → sessionId` 的 entry 直接复用，agent 也按 entry 里绑的来，跟 binding 无关。改 binding 之前/之后都要查 `agents/<agent>/sessions/sessions.json` 把这个 entry 删掉，否则即使 binding 改对了，session 缓存仍把消息路由回旧 agent。

---

#### awada 插件依赖（ws + zod）

- **Docker 部署**：Dockerfile wiseflow-layer 阶段 `COPY awada/ + npm install --omit=dev`，ws+zod 烘进 `/opt/openclaw/awada/node_modules`。
- **源码部署**：`apply-addons.sh` 自动 `cd awada && npm install --omit=dev`（哈希守卫 `.awada-pkg-hash`，幂等）。
- **关键点**：awada 插件运行时从自身 `awada/node_modules` 解析 ws/zod，**不**走 `~/.openclaw/node_modules`（不在向上解析链），故必须装在 awada 局部，不能靠统一依赖扫描。
- **Phase 4 已完成**（2026-07-07）：awada 改 HTTP/WS transport 调 relay 网关，ioredis 已从 deps 移除，预装步骤改装 ws+zod。proactive-send skill 同步迁 HTTP 网关，不再依赖 ioredis。
- **IT engineer 介入时机**：仅当日志报 `Cannot find module 'ws'`（plugin=awada）且上述预装漏跑时，按 `awada-channel-setup` SKILL 步骤 1 手动补装。

---

## 运行中持续积累的经验

### exec-approvals.json 修改经验
- **不要直接修改 `exec-approvals.json`**:该文件由 `setup-crew.sh` 自动生成,每次升级或执行脚本时会被覆盖。
- **正确做法**:在对应 agent 的 workspace 下创建/修改 `ALLOWED_COMMANDS` 文件,格式参考 `workspace-sales-cs/ALLOWED_COMMANDS`。
- **文件格式**:每行 `+./skills/xxx/scripts/xxx.sh`,相对于 workspace 根目录。
- **同步命令**:修改后执行 `cd <WISEFLOW_PROJECT_ROOT> && ./scripts/setup-crew.sh` 使配置生效。

### 某个 agent 全报 "Something went wrong"处置方案

1. **看 gateway-error.log**(`/home/wukong/wiseflow-pro/logs/gateway-error.log`),找 `embedded run agent end: isError=true` + 紧跟的 `error=LLM request failed` 行。
2. **看 sessions.json 里那个 agent 的 modelOverride**(`~/.openclaw/agents/<agent>/sessions/sessions.json`,key 是 `agent:<agent>:feishu:direct:<user_ouid>`):
   - 如果有 `modelOverride` + `modelOverrideSource: "user"` → 说明之前 `/model <xx>` 把会话锁死在那个模型上了。
   - **修复**:用户在该 agent 对话里发 `/model <默认主模型>`,或 IT Engineer 删掉 sessions.json 里的 `modelOverride/providerOverride/modelOverrideSource` 三个字段(注意先 `cp` 备份 `.bak-<日期>`)。
   - **原因**:用户用 `/model` 切换是持久化的,`/new` 不会清。
3. **如果错误是 `max_tokens` 超过 provider 上限**:改 `openclaw.json` 里那个模型的 `maxTokens`。注意备份,hot-reload 通常生效。
