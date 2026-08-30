#!/usr/bin/env node
/**
 * send.mjs — Proactive awada message sender (HTTP gateway transport)
 *
 * Usage:
 *   node scripts/send.mjs \
 *     --user-id-external "黄子奇ᐪᒻ" \
 *     --text "您好，昨天咱们聊过专业版的事，不知道今天方便看看吗？"
 *
 * 走 relay 网关 POST /api/v1/awada/outbound?lane=<lane>（见 awada-extension/src/send.ts
 * 的 postOutbound，契约见 docs/AWADA-CLIENT-TRANSPORT.md §3）。
 * awadaKey / lane 从 ~/.openclaw/openclaw.json 的 channels.awada 读取；
 * relayBaseUrl 缺省时回退到官方 relay 域名 https://relay.openclaw-for-business.com。
 * lane 缺省时服务器默认使用 "User" lane。
 * channel_id 和 tenant_id 固定为 "0"（私聊）。platform 由 relay 按 lane 绑定推导，客户端不发。
 * 成功：打印 streamId（exit 0）；失败：打印错误到 stderr（exit 1）。
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const DEFAULT_RELAY_BASE_URL = "https://relay.openclaw-for-business.com";

// ── Arg parsing ──────────────────────────────────────────────────────────────

function getArg(name) {
  const idx = process.argv.indexOf(name);
  if (idx === -1 || idx >= process.argv.length - 1) return null;
  return process.argv[idx + 1];
}

const userIdExternal = getArg("--user-id-external");
const text = getArg("--text");

if (!userIdExternal || !text) {
  console.error("Usage: node send.mjs --user-id-external <id> --text <message>");
  process.exit(1);
}

// ── Load openclaw config ─────────────────────────────────────────────────────

const configPath = join(homedir(), ".openclaw", "openclaw.json");
let cfg;
try {
  cfg = JSON.parse(readFileSync(configPath, "utf8"));
} catch (err) {
  console.error(`❌ Cannot read config: ${configPath}: ${err.message}`);
  process.exit(1);
}

const awadaCfg = cfg?.channels?.awada ?? {};
const { awadaKey, lane } = awadaCfg;
const relayBaseUrl = awadaCfg.relayBaseUrl || DEFAULT_RELAY_BASE_URL;

if (!awadaKey) {
  console.error("❌ channels.awada 需配置 awadaKey");
  process.exit(1);
}

// ── POST /outbound ───────────────────────────────────────────────────────────
// platform 由 relay 按 lane 绑定推导，客户端不发；channel_id / user_id_external 必填。

const url = `${relayBaseUrl.replace(/\/+$/, "")}/api/v1/awada/outbound?lane=${encodeURIComponent(lane)}`;
const body = {
  payload: [{ type: "text", text }],
  meta: {
    channel_id: "0",
    user_id_external: userIdExternal,
    tenant_id: "0",
  },
};

try {
  const res = await fetch(url, {
    method: "POST",
    headers: { "X-Awada-Key": awadaKey, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const errBody = await res.json();
      if (errBody?.error?.code || errBody?.error?.message) {
        detail = `${res.status}: ${errBody.error.code ?? ""} ${errBody.error.message ?? ""}`.trim();
      }
    } catch {
      // non-json error body
    }
    console.error(`❌ outbound POST failed: ${detail}`);
    process.exit(1);
  }
  const json = await res.json();
  const streamId = json?.data?.streamId ?? "";
  console.log(streamId);
} catch (err) {
  console.error(`❌ outbound POST error: ${err.message}`);
  process.exit(1);
}
