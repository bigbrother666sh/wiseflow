# awada（client 侧）

## 为什么需要 awada？

部分第三方消息服务提供商（企微 bot、个微 bot）要求固定公网 IP 接收 webhook，而 openclaw 多为本地部署。awada 在公网中转消息到本地 openclaw 实例。

## 架构（拆分后）

```
微信用户
   │  (消息)
   ▼
provider service ──webhook──► awada-server
                                      │
                                   HTTP/WS 网关（X-Awada-Key 鉴权）
                                      │
                                      ▼
                            awada-extension（本地 openclaw，本仓）
                                      │
                                   openclaw agent
                                      │
                                      ▼
                            awada-server ──► 微信用户（回复）
```

**传输契约**：见 `docs/AWADA-CLIENT-TRANSPORT.md`（唯一耦合面）。

- **inbound**（server 写 / bot 读）：bot 通过 `WS /api/v1/awada/inbound?lane=` 拉取，处理完发 `{type:"ack",id}`。
- **outbound**（bot 写 / server 读）：bot 通过 `POST /api/v1/awada/outbound?lane=` 回执，`meta` 必填 `channel_id`/`user_id_external`（从 inbound `event.meta` 原样回传）；`platform` 回复时回传、主动外呼省略。
- **Redis** → relay 内部，**不对客户端暴露**（D2）。客户端最少只需配 `awadaKey`。

**核心组件（拆分后归属）：**
- **awada-server** → relay 仓 `services/awada-server/`。客户端不部署、不持凭据。
- **awada-extension** → 本仓 `awada/`。openclaw channel 插件，走 HTTP/WS 调 relay 网关。

## 启用 awada-extension

### 安装依赖（必做一次）

```bash
cd /path/to/openclaw/awada
pnpm install --prod
```

典型报错信号：`Cannot find module 'ws'`（缺依赖）。

### 配置

openclaw 配置文件中添加 `channels.awada` 节点：

```json
{
  "channels": {
    "awada": {
      "awadaKey": "<AWADA_KEY>"
    }
  }
}
```

> **传输改造点**：原 `redisUrl` 字段已作废，替换为 `relayBaseUrl` + `awadaKey`。extension 走 `WS /api/v1/awada/inbound?lane=`（读 inbound + ack）+ `POST /api/v1/awada/outbound?lane=`（写回执），带 `X-Awada-Key` header。Redis 直连模式不再支持。
>
> `awadaKey` 与签名服务用的 `OFB_KEY` 是两份独立凭证，relay admin 分别签发。`lane` 在 relay 侧 provision 时已绑死 platform，客户端不发 `platform`。

**awada-extension 配置项：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | `true` | 是否启用 |
| `awadaKey` | string | — | awada key，**必填**，由 relay admin 签发（含 `awada:lane:<laneId>` scope），作为 `X-Awada-Key` header 发出 |
| `relayBaseUrl` | string | `https://relay.openclaw-for-business.com` | relay 网关端点（http/https）；官方域名可不配 |
| `lane` | string | `""`（server 默认 `User`） | 订阅的 lane，可选；不传时服务器默认使用 `User` lane |
| `dmPolicy` | string | `"open"` | `open`/`pairing`/`allowlist` |
| `allowFrom` | string[] | `[]` | `allowlist` 模式下允许的用户 ID |
| `perMsgMaxLen` | number | — | 单条消息最大字符数，超长自动拆分 |

客服场景推荐配置（含消息长度限制 + 用户会话隔离）：

```json
{
  "channels": {
    "awada": {
      "awadaKey": "<AWADA_KEY>",
      "perMsgMaxLen": 500
    }
  },
  "session": { "dmScope": "per-channel-peer" }
}
```

> `perMsgMaxLen: 500`：超长回复自动拆分，每条 ≤500 字符（微信单消息长度限制）。
> `session.dmScope: "per-channel-peer"`：每个微信用户独享 session，上下文隔离。

## 传输语义

- **WS 长连接 + ack**：extension 启动后开一条 WS 到 relay 网关，relay 推 `{id,event}` 帧，extension 处理完（含 POST 回执）后发 `{type:"ack",id}`。未 ack 的事件留在 PEL，断线重连后由网关 XAUTOCLAIM 回收重投（min-idle 65s）。
- **至少一次**：极少数情况下（ack 已发但网关进程恰好崩溃在 ack 处理中）同一条会重投。bot 侧业务应按 `event_id` 幂等。
- **session_lock / processed 去重在网关侧**，client 不碰锁、不做去重。
- **回执路由**：relay 据回执 `meta.platform`/`channel_id`/`user_id_external` 路由回 platform，**不按 `source_event_id` 反查**。extension 从 inbound `event.meta` 原样回传这些字段。

## 多 Bot / 多实例

- **多 bot**：在 relay 侧 awada-server 配置多个 bot，每个 bot 绑定一个 lane（1:1）。客户端用不同 `awadaKey`/`lane` 订阅（`lane` 可省略，server 默认 `User`）。
- **多 openclaw 实例**：不同实例订阅不同 lane。
- 客户端无需感知 Redis db 隔离（relay 内部处理）。
