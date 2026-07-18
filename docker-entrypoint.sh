#!/bin/bash
# docker-entrypoint.sh — wiseflow-client 容器入口
#
# 流程（plan §六 entrypoint 运行期）：
#   1. 读 env 渲染 daemon.env（key 占位 → 真实值）
#   2. 注入 OFB_KEY / relay 端点到各 skill 配置
#   3. node openclaw.mjs gateway（非 systemd，--restart=always 保活）
#   4. 检测 weixin 未绑 → qrcode-terminal 输出 stdout + UI(18789) 兜底
#
# Phase 0 骨架：框架流程就位，步骤 1/2 的具体渲染待 Phase 6 填实。
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-/root/.openclaw}"
DAEMON_ENV="$OPENCLAW_HOME/daemon.env"
GATEWAY_PORT="${GATEWAY_PORT:-18789}"

echo "[entrypoint] wiseflow-client starting, OPENCLAW_HOME=$OPENCLAW_HOME"

# ── 1. 加载 daemon.env ─────────────────────────────────────────────────────
# 裸机部署走 systemd EnvironmentFile=-/root/.openclaw/daemon.env；
# Docker 不跑 systemd，这里手动 source daemon.env 把 KEY=value 导入环境。
# 优先级：docker run -e 传的环境变量 > daemon.env 里的值。
#   实现：先 set -a（让 source 的变量自动 export），source 后 docker run -e
#   传入的变量已经存在于环境，source 不会覆盖已存在的环境变量（bash source 语义）。
# daemon.env 由 install.sh（裸机）或用户手动/it-engineer skill 写入，落 named volume 持久化。
if [ ! -f "$DAEMON_ENV" ]; then
  # 首次启动：从 template 拷一份，用户编辑后 docker restart 生效
  if [ -f "$OPENCLAW_HOME/daemon.env.template" ]; then
    cp "$OPENCLAW_HOME/daemon.env.template" "$DAEMON_ENV"
    chmod 600 "$DAEMON_ENV"
    echo "[entrypoint] 首次启动：已从 daemon.env.template 拷贝到 $DAEMON_ENV"
    echo "[entrypoint]   请编辑该文件填入 API keys，然后 docker restart 生效"
  fi
fi
if [ -f "$DAEMON_ENV" ]; then
  echo "[entrypoint] loading $DAEMON_ENV"
  set -a
  # shellcheck disable=SC1090
  source "$DAEMON_ENV"
  set +a
else
  echo "[entrypoint] WARN: $DAEMON_ENV 不存在，用环境变量直传"
fi

# ── 2. 注入 relay 端点 + OFB_KEY 到 skill 配置 ─────────────────────────────
# relay 无状态多租户模型（2026-07-06）：RELAY_BASE_URL + OFB_KEY 作为环境变量注入，
#   各 skill 脚本从 env 读取。凭据按 skill 分置：
#   - wxwork-moments / wxwork-drive：WXWORK_CORP_ID + WXWORK_CORP_SECRET 从 daemon.env 读
#   - wx-mp-publisher：多账号凭据在 skill 目录 accounts.json（Agent 帮用户维护，gitignore）
#   - xhs-publish / bilibili-publish 等：业务凭据各自管理
export RELAY_BASE_URL="${RELAY_BASE_URL:-https://relay.wiseflow.example.com}"
# OFB_KEY 必须由用户传入
if [ -z "${OFB_KEY:-}" ]; then
  echo "[entrypoint] ERROR: OFB_KEY 未设置。容器需 -e OFB_KEY=<产品方发放的 key>" >&2
  exit 1
fi

# ── 2.5 虚拟显示 + VNC 远程查看栈 ──────────────────────────────────────────
# camoufox 有头登录场景：用户需看到浏览器界面才能手动扫码/验证。
# Docker 容器无物理显示器，用 Xvfb 虚拟帧缓冲 + fluxbox 窗口管理器 +
# x11vnc 把 X 显示通过 VNC 暴露 + noVNC/websockify 让用户浏览器访问 :6080。
#
# 访问方式：浏览器打开 http://<容器IP>:6080/vnc.html
#
# DISPLAY 也可由 daemon.env 注入；这里统一设 :99（Xvfb 默认 display 号）。
DISPLAY="${DISPLAY:-:99}"
export DISPLAY

# 启动 Xvfb（虚拟帧缓冲，模拟 X 显示）
Xvfb "$DISPLAY" -screen 0 1280x800x24 -ac >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 1  # 等 X server 就绪

# 启动 fluxbox（轻量窗口管理器，camoufox 有头需要 WM）
fluxbox >/tmp/fluxbox.log 2>&1 &
FLUXBOX_PID=$!

# 启动 x11vnc（把 X 显示通过 VNC 暴露）
# -forever: 保持运行，不退出
# -shared: 允许多客户端连接
# -rfbport: VNC 端口 5900
x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
X11VNC_PID=$!

# 启动 websockify（noVNC 前端，HTTP→VNC 桥）
# 监听 6080，转发到 localhost:5900（x11vnc）
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/websockify.log 2>&1 &
WEBSOCKIFY_PID=$!

echo "[entrypoint] 虚拟显示栈已启动:"
echo "  Xvfb PID=$XVFB_PID (display=$DISPLAY, 1280x800x24)"
echo "  fluxbox PID=$FLUXBOX_PID"
echo "  x11vnc PID=$X11VNC_PID (VNC :5900)"
echo "  websockify PID=$WEBSOCKIFY_PID (noVNC :6080)"
echo "[entrypoint] 浏览器访问 http://<容器IP>:6080/vnc.html 看容器内界面"

# ── 2.6 camoufox 指纹模板 lazy 生成 ────────────────────────────────────────
# build 期不跑 camoufox-cli（Firefox sandbox 在 docker build cap 下 EPERM）。
# 容器首次启动时现生成指纹模板，落 /root/.openclaw/logins/_template/。
# 需 docker run --cap-add SYS_ADMIN（Firefox sandbox 需要 user namespace）。
TEMPLATE_DIR="$OPENCLAW_HOME/logins/_template"
if [ ! -f "$TEMPLATE_DIR/camoufox-cli.json" ]; then
  echo "[entrypoint] baking camoufox fingerprint template..."
  rm -rf /root/.camoufox-cli/profiles/_template
  if camoufox-cli --session _template --persistent --json open about:blank >/dev/null 2>&1; then
    camoufox-cli --session _template close >/dev/null 2>&1 || true
    cp /root/.camoufox-cli/profiles/_template/camoufox-cli.json "$TEMPLATE_DIR/" 2>/dev/null || true
    echo "[entrypoint] camoufox fingerprint template baked to $TEMPLATE_DIR"
  else
    echo "[entrypoint] WARN: camoufox fingerprint template bake failed." >&2
    echo "[entrypoint]   确认 docker run 带 --cap-add SYS_ADMIN；或运行时首会话现生成。" >&2
  fi
  camoufox-cli close --all >/dev/null 2>&1 || true
fi

# ── 3. 起 gateway ───────────────────────────────────────────────────────────
# TODO(Phase 6): 真正的入口是 node openclaw.mjs gateway。此处先 exec 占位。
OPENCLAW_BIN="${OPENCLAW_BIN:-/opt/openclaw/openclaw/openclaw.mjs}"
if [ -f "$OPENCLAW_BIN" ]; then
  echo "[entrypoint] launching gateway: node $OPENCLAW_BIN gateway"

  # ── 4. weixin 二维码（后台 fork，gateway ready 后触发）──────────────────────
  # gateway 是 exec 启动（PID 1），此段必须在 exec 之前 fork。
  # 后台子进程等 gateway HTTP 就绪（轮询 /healthz）→ 检测 weixin 未绑 →
  # 跑 `channels login --channel openclaw-weixin`，二维码输出 stdout（docker logs 可见）。
  # 已绑（存在 channels/openclaw-weixin.json）则跳过，不重复出码。
  (
    for _ in $(seq 1 30); do
      if curl -sf "http://127.0.0.1:${GATEWAY_PORT}/healthz" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    if [ -f "$OPENCLAW_HOME/channels/openclaw-weixin.json" ]; then
      echo "[entrypoint] openclaw-weixin 已绑定，跳过二维码"
    else
      echo "[entrypoint] openclaw-weixin 未绑定，启动登录二维码流程..."
      cd /opt/openclaw/openclaw && \
        node scripts/run-node.mjs channels login --channel openclaw-weixin 2>&1 | \
        tee -a /tmp/weixin-login.log
    fi
  ) &

  exec node "$OPENCLAW_BIN" gateway
else
  echo "[entrypoint] WARN: $OPENCLAW_BIN 不存在（Phase 6 build 产物未 bake）。退出。" >&2
  exit 0
fi
