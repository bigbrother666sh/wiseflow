# config/ — wiseflow-client 运行态配置

build 期由 Dockerfile 阶段 3（wiseflow-layer）把这里的 `openclaw.json` 放到
`/root/.openclaw/openclaw.json`，`daemon.env.template` 由 entrypoint 渲染成
`/root/.openclaw/daemon.env`，`workspace-skeleton/` 复制到各 crew workspace。

## 文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `openclaw.json` | openclaw 主配置（crew list / addons / models / channels） | 🟡 seed（复制自 `config-templates/openclaw.json`），Phase 7 改成 3-crew client 目标态 |
| `daemon.env.template` | daemon 环境变量模板，entrypoint 渲染 | ✅ 占位就位（AWK_API_KEY / OFB_KEY / RELAY_BASE_URL / SMTP_*） |
| `workspace-skeleton/` | 通用 workspace 骨架 | ✅ 结构就位，运行期内容不进镜像 |

## openclaw.json 目标态（Phase 7）

seed 现在是现仓的全量配置。Phase 7 改成 client 目标：

- **crew list**：`main`（DEFAULT，绑 openclaw-weixin）+ `it-engineer`；`sales-cs` 默认 seed 但**不在 list**（D10，启用由 IT engineer 操作）
- **addons**：删 `officials` / `official-plus`（D8 扁平化后无 addon 结构）；保留 `openclaw-weixin`
- **awada**：`enabled: false`（D10）
- **models**：保留 awk provider（用户 AWK_API_KEY）；视频生成模型走 relay（不直配上游 key，D12）
- **browser**：headless=true（D18 camoufox 主）；保留 patchright override 供 fallback

## relay 端点注入

entrypoint 把 `RELAY_BASE_URL` 派生成各子端点写入 skill 配置（见 `daemon.env.template` 注释）。用户只需配 `AWK_API_KEY` + `OFB_KEY`，relay 端点固定。
