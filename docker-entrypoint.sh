#!/usr/bin/env bash
set -euo pipefail

XIAOBEI_ROOT=/opt/xiaobei
OPENCLAW_HOME=${OPENCLAW_HOME:-/root/.openclaw}
CAMOUFOX_HOME=${CAMOUFOX_HOME:-/root/.camoufox-cli}
RUNTIME_SEED=/opt/xiaobei/runtime-seed/openclaw
DOTENV="$OPENCLAW_HOME/.env"
DAEMON_ENV="$OPENCLAW_HOME/daemon.env"

fail() {
  echo "[xiaobei] ERROR: $*" >&2
  exit 1
}

bootstrap_runtime_state() {
  if [ ! -f "$OPENCLAW_HOME/openclaw.json" ]; then
    [ -d "$RUNTIME_SEED" ] || fail "runtime seed is missing: $RUNTIME_SEED"
    echo "[xiaobei] initializing persistent OpenClaw state"
    install -d -m 700 "$OPENCLAW_HOME"
    cp -a "$RUNTIME_SEED/." "$OPENCLAW_HOME/"
  fi
  install -d -m 700 "$CAMOUFOX_HOME"
  chmod 700 "$OPENCLAW_HOME" "$CAMOUFOX_HOME"
}

load_runtime_environment() {
  # Compose variables take precedence over persisted configuration. The seed
  # contains placeholders, which must never shadow a supplied AWK_API_KEY.
  local supplied_awk_api_key=${AWK_API_KEY:-}

  if [ -f "$DAEMON_ENV" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$DAEMON_ENV"
    set +a
  fi

  if [ -f "$DOTENV" ]; then
    local clean_dotenv
    clean_dotenv=$(mktemp)
    grep -v '__FILL_.*__' "$DOTENV" > "$clean_dotenv" || true
    set -a
    # shellcheck disable=SC1090
    . "$clean_dotenv"
    set +a
    rm -f "$clean_dotenv"
  fi

  if [ -n "$supplied_awk_api_key" ]; then
    export AWK_API_KEY="$supplied_awk_api_key"
  fi
}

ensure_gateway_token() {
  if [ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]; then
    umask 077
    OPENCLAW_GATEWAY_TOKEN=$(node -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("base64url"))')
    printf '\nOPENCLAW_GATEWAY_TOKEN=%s\n' "$OPENCLAW_GATEWAY_TOKEN" >> "$DOTENV"
    chmod 600 "$DOTENV"
    export OPENCLAW_GATEWAY_TOKEN
    echo "[xiaobei] generated and persisted a gateway token"
  fi
}

start_display_stack() {
  export DISPLAY=${DISPLAY:-:99}
  Xvfb "$DISPLAY" -screen 0 1280x800x24 -ac >/tmp/xiaobei-xvfb.log 2>&1 &
  fluxbox >/tmp/xiaobei-fluxbox.log 2>&1 &
  x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 >/tmp/xiaobei-x11vnc.log 2>&1 &
  websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/xiaobei-websockify.log 2>&1 &
}

bootstrap_runtime_state
load_runtime_environment

if [ -z "${AWK_API_KEY:-}" ] || [[ "$AWK_API_KEY" == __FILL_*__ ]]; then
  fail "AWK_API_KEY is required; run: AWK_API_KEY=<key> docker compose up -d"
fi

ensure_gateway_token
start_display_stack

echo "[xiaobei] starting gateway"
cd "$XIAOBEI_ROOT/openclaw"
exec pnpm openclaw gateway --allow-unconfigured
