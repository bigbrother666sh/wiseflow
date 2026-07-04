#!/usr/bin/env bash
# export-cookies.sh — One-step cookie export from browser tab to login-manager storage
#
# Usage: export-cookies.sh <wsUrl> <domain> <platform>
#
# Arguments:
#   wsUrl    — CDP WebSocket URL from `browser action=tabs` (wsUrl field)
#   domain   — Domain filter (e.g., "xiaohongshu.com", "douyin.com")
#   platform — Platform name for login-manager storage (e.g., "xhs-publish", "douyin")
#
# This script:
#   1. Connects to CDP WebSocket and extracts all cookies for the domain
#   2. Gets the User-Agent from the page
#   3. Writes the session to ~/.openclaw/logins/{platform}.json via login-manager
#
# Exit codes:
#   0 — success
#   1 — error
#
# Requires: Node.js 22+ (for built-in WebSocket and --experimental-strip-types)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -ne 3 ]; then
  echo "Usage: export-cookies.sh <wsUrl> <domain> <platform>" >&2
  echo "" >&2
  echo "  wsUrl    CDP WebSocket URL from browser tabs (wsUrl field)" >&2
  echo "  domain   Domain filter (e.g. xiaohongshu.com)" >&2
  echo "  platform Platform name for login-manager (e.g. xhs-publish)" >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  export-cookies.sh ws://127.0.0.1:18800/devtools/page/ABC123 xiaohongshu.com xhs-publish" >&2
  exit 1
fi

WS_URL="$1"
DOMAIN="$2"
PLATFORM="$3"

# Step 1: Extract cookies via CDP
echo "[export-cookies] Extracting cookies for ${DOMAIN}..." >&2
COOKIE_JSON=$(node --experimental-strip-types "${SCRIPT_DIR}/extract_cookies.ts" "$WS_URL" "$DOMAIN" 2>/dev/null)

if [ -z "$COOKIE_JSON" ]; then
  echo "[export-cookies] ERROR: extract_cookies.ts returned empty output" >&2
  exit 1
fi

# Parse cookieString from JSON output
COOKIE_STRING=$(echo "$COOKIE_JSON" | node -e "
  const chunks = [];
  process.stdin.on('data', c => chunks.push(c));
  process.stdin.on('end', () => {
    try {
      const d = JSON.parse(Buffer.concat(chunks).toString());
      if (!d.ok) { process.stderr.write('ERROR: ' + (d.error || 'unknown') + '\n'); process.exit(1); }
      process.stdout.write(d.cookieString || '');
    } catch (e) { process.stderr.write('ERROR: failed to parse cookie JSON\n'); process.exit(1); }
  });
")

if [ -z "$COOKIE_STRING" ]; then
  echo "[export-cookies] ERROR: no cookies extracted for domain ${DOMAIN}" >&2
  exit 1
fi

COOKIE_COUNT=$(echo "$COOKIE_JSON" | node -e "
  const chunks = [];
  process.stdin.on('data', c => chunks.push(c));
  process.stdin.on('end', () => {
    const d = JSON.parse(Buffer.concat(chunks).toString());
    process.stdout.write(String(d.cookieCount || 0));
  });
")
echo "[export-cookies] Got ${COOKIE_COUNT} cookies for ${DOMAIN}" >&2

# Step 2: Get User-Agent from the page via CDP
UA_JSON=$(node --experimental-strip-types -e "
const wsUrl = process.argv[1];
const ws = new WebSocket(wsUrl);
let msgId = 0;
function cdpReq(method, params) {
  return JSON.stringify({ id: ++msgId, method, params: params || {} });
}
const timeout = setTimeout(() => { ws.close(); process.stdout.write(JSON.stringify({ok: false})); process.exit(0); }, 10000);
ws.addEventListener('open', () => {
  ws.send(cdpReq('Network.enable'));
  ws.send(cdpReq('Runtime.evaluate', { expression: 'navigator.userAgent', returnByValue: true }));
});
ws.addEventListener('message', (ev) => {
  try {
    const msg = JSON.parse(ev.data);
    if (msg.id === 2 && msg.result?.result?.value) {
      clearTimeout(timeout);
      ws.close();
      process.stdout.write(JSON.stringify({ok: true, ua: msg.result.result.value}));
    }
  } catch {}
});
ws.addEventListener('error', () => { clearTimeout(timeout); process.stdout.write(JSON.stringify({ok: false})); });
" "$WS_URL" 2>/dev/null)

USER_AGENT=$(echo "$UA_JSON" | node -e "
  const chunks = [];
  process.stdin.on('data', c => chunks.push(c));
  process.stdin.on('end', () => {
    try {
      const d = JSON.parse(Buffer.concat(chunks).toString());
      process.stdout.write(d.ok ? (d.ua || '') : '');
    } catch { process.stdout.write(''); }
  });
")

if [ -z "$USER_AGENT" ]; then
  USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
  echo "[export-cookies] WARNING: could not get UA from page, using default" >&2
fi

echo "[export-cookies] User-Agent: ${USER_AGENT:0:60}..." >&2

# Step 3: Write to login-manager storage
SESSION_JSON=$(node -e "
  process.stdout.write(JSON.stringify({ cookies: process.argv[1], user_agent: process.argv[2] }));
" "$COOKIE_STRING" "$USER_AGENT")

echo "$SESSION_JSON" | node --experimental-strip-types "${SCRIPT_DIR}/login_manager.ts" write "$PLATFORM" >/dev/null 2>&1

WRITE_EXIT=$?
if [ $WRITE_EXIT -ne 0 ]; then
  echo "[export-cookies] ERROR: failed to write session for ${PLATFORM} (exit ${WRITE_EXIT})" >&2
  exit 1
fi

echo "[export-cookies] ✅ Session saved for ${PLATFORM} (${COOKIE_COUNT} cookies)" >&2
# Output summary JSON for caller
node -e "
  process.stdout.write(JSON.stringify({
    ok: true,
    platform: process.argv[1],
    cookieCount: parseInt(process.argv[2]),
    domain: process.argv[3]
  }));
" "$PLATFORM" "$COOKIE_COUNT" "$DOMAIN"
