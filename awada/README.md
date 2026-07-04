# awada（client 侧）

> 产品拆分后本仓承担 **wiseflow-client** 角色。awada-server 已整体迁出至 relay 仓 `services/awada-server/`（决策 D4）。本仓仅保留 **awada-extension** 作为 openclaw channel，走 HTTP/WS transport 调 relay（决策 D2），不再直连 Redis。

## 为什么需要 awada？

部分第三方消息服务提供商（企微 bot、个微 bot）要求固定公网 IP 接收 webhook，而 openclaw 多为本地部署。awada 在公网中转消息到本地 openclaw 实例。

## 架构（拆分后）

```
微信用户
   │  (消息)
   ▼
WorkTool / QiweAPI ──webhook──► awada-server（relay 仓 services/awada-server/）
                                      │
                                   HTTP/WS transport（OFB_KEY 鉴权）
                                      │
                                      ▼
                            awada-extension（本地 openclaw，本仓）
                                      │
                                   openclaw agent
                                      │
                                      ▼
                            awada-server ──► 微信用户（回复）
```

**核心组件（拆分后归属）：**
- **awada-server** → relay 仓 `services/awada-server/`。客户端不部署、不持凭据。
- **awada-extension** → 本仓 `awada/`。openclaw channel 插件，走 HTTP/WS 调 relay。
- **Redis** → relay 内部，**不对客户端暴露**（D2）。客户端只见 `RELAY_BASE_URL` + `OFB_KEY`。

## 启用 awada-extension

### 安装依赖（必做一次）

```bash
cd /path/to/openclaw/awada
pnpm install --prod
```

典型报错信号：`Cannot find module 'ioredis'`（缺依赖）。

### 配置

openclaw 配置文件中添加 `channels.awada` 节点：

```json
{
  "channels": {
    "awada": {
      "enabled": true,
      "relayBaseUrl": "https://relay.wiseflow.example.com",
      "ofbKey": "<OFB_KEY>",
      "lane": "user",
      "platform": "worktool:mybot"
    }
  }
}
```

> **Phase 4 改造点**：原 `redisUrl` 字段替换为 `relayBaseUrl` + `ofbKey`，extension 走 `GET /api/v1/awada/outbound?lane=`（long-poll/WS）+ `POST /api/v1/awada/inbound`，带 `X-OFB-Key` header。Redis 直连模式作废。

**awada-extension 配置项（拆分后）：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | `true` | 是否启用 |
| `relayBaseUrl` | string | — | relay 端点，**必填**（由 entrypoint 从 `RELAY_BASE_URL` 注入） |
| `ofbKey` | string | — | OFB_KEY，**必填**（由 entrypoint 从 `OFB_KEY` 注入） |
| `lane` | string | `"user"` | 订阅的 lane |
| `platform` | string | — | 平台标识，主动发消息时必填 |
| `dmPolicy` | string | `"open"` | `open`/`pairing`/`allowlist` |
| `allowFrom` | string[] | `[]` | `allowlist` 模式下允许的用户 ID |
| `perMsgMaxLen` | number | — | 单条消息最大字符数，超长自动拆分 |

客服场景推荐配置（含消息长度限制 + 用户会话隔离）：

```json
{
  "channels": {
    "awada": {
      "enabled": true,
      "relayBaseUrl": "https://relay.wiseflow.example.com",
      "ofbKey": "<OFB_KEY>",
      "lane": "user",
      "platform": "worktool:mybot",
      "dmPolicy": "open",
      "perMsgMaxLen": 500
    }
  },
  "session": { "dmScope": "per-channel-peer" }
}
```

> `perMsgMaxLen: 500`：超长回复自动拆分，每条 ≤500 字符（微信单消息长度限制）。
> `session.dmScope: "per-channel-peer"`：每个微信用户独享 session，上下文隔离。

## 多 Bot / 多实例

- **多 bot**：在 relay 侧 awada-server `.env` 增加 `BOT_2_*`、`BOT_3_*`，每个 bot 分配不同 lane。
- **多 openclaw 实例**：不同实例订阅不同 lane，或使用不同 consumerGroup。
- 客户端无需感知 Redis db 隔离（relay 内部处理）。

## awada-server 在哪？

`services/awada-server/` 已迁至 relay 仓（`git-server:repos/wiseflow-relay.git`），交接文档见该仓 `docs/HANDOVER.md`。本仓不再包含 server 代码。启用 sales-cs（D10）由 IT engineer 操作改 `enabled: true` + 软链 business_knowledge。
