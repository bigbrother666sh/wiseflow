#!/usr/bin/env bash
# docker-bootstrap.sh — 构建镜像的 immutable 应用层（等价于"跑完 install.sh 装好后"状态）
#
# 与裸机 install.sh 区别：
#   - 不拉远程仓库（openclaw 源码已由 Dockerfile COPY 进来）
#   - 不跑 daemon install / 不交互收密钥（容器无 systemd，密钥走运行时环境变量）
#   - 不重启 gateway（构建阶段没运行实例）
#
# 复用裸机安装的同一套底层脚本，保证 patch / skills / wrappers / 依赖 / 编译语义与裸机同源：
#   - patches/camoufox-cli/build.sh         反指纹浏览器 CLI fork
#   - scripts/apply-addons.sh               patch 应用 + skills + crew workspace + 编译
#   - scripts/setup-crew.sh                 crew workspace 初始化（由 apply-addons 内部触发）
#   - weixin 插件在线 plugins install        （逻辑内联在此，不调独立的 install-weixin-channel.sh）
set -euo pipefail

PROJECT_ROOT="${XIAOBEI_ROOT:-/opt/xiaobei}"
OPENCLAW_HOME="${OPENCLAW_HOME:-/root/.openclaw}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_HOME/openclaw.json}"

# ─── 校验源码树 ────────────────────────────────────────────────────
[ -d "$PROJECT_ROOT/openclaw/.git" ] || {
    echo "[docker-bootstrap] ❌ openclaw 源码树缺失或无 .git（apply-addons 需 object store）" >&2
    exit 1
}
[ -x "$PROJECT_ROOT/scripts/apply-addons.sh" ] || {
    echo "[docker-bootstrap] ❌ scripts/apply-addons.sh 缺失" >&2
    exit 1
}

mkdir -p "$OPENCLAW_HOME"

# ─── 放置 config template（apply-addons 会同步 agents[].skills 节点）────────
# template 内 apiKey 字段是 ${AWK_API_KEY} placeholder，构建期 AWK_API_KEY 未设故留 placeholder，
# 由 entrypoint 在首启时渲染成真实值。plugins.load.paths 的 ${XIAOBEI_HOME} 这里直接解析成
# /opt/xiaobei（容器内固定）写回，避免运行时 env ref 解析。
cp "$PROJECT_ROOT/config-templates/openclaw.json" "$OPENCLAW_CONFIG_PATH"
cp "$PROJECT_ROOT/config/daemon.env.template" "$OPENCLAW_HOME/daemon.env"
cp "$PROJECT_ROOT/config/.env.template" "$OPENCLAW_HOME/.env"
chmod 600 "$OPENCLAW_HOME/daemon.env" "$OPENCLAW_HOME/.env"

# 把 template 内 ${XIAOBEI_HOME} 解析成容器内固定路径写回
node -e '
    const fs = require("fs");
    const p = process.argv[1];
    let raw = fs.readFileSync(p, "utf8");
    raw = raw.replace(/\$\{XIAOBEI_HOME\}/g, "/opt/xiaobei");
    fs.writeFileSync(p, raw);
' "$OPENCLAW_CONFIG_PATH"

# ─── camoufox-cli fork 构建 + 全局安装 ──────────────────────────────
# 这个 fork 是 browser-guide 等技能用的浏览器 CLI。构建 + 全局 npm install -g 替换上游版。
# Firefox 二进制由后续 camoufox-cli install 拉取（~557MB，幂等）。
echo "[docker-bootstrap] building camoufox-cli fork..."
"$PROJECT_ROOT/patches/camoufox-cli/build.sh"

# ─── apply-addons：patch 应用 + skills 安装 + crew workspace + 编译 dist ──
# --force        覆盖已有 workspace（构建态从零起，不会冲突）
# --no-restart   构建态无运行实例可重启
echo "[docker-bootstrap] applying addons (patches + skills + crews + build)..."
"$PROJECT_ROOT/scripts/apply-addons.sh" --force --no-restart

# ─── camoufox-cli install：拉 Firefox 二进制 ──────────────────────
# 幂等：已装且版本一致时打印 "already up to date" 并返回
echo "[docker-bootstrap] ensuring camoufox Firefox binary..."
camoufox-cli install || echo "[docker-bootstrap] ⚠️ camoufox-cli install failed（可后续手动 camoufox-cli install）"

# ─── 预装 openclaw-weixin 插件 ────────────────────────────────────
# 与裸机 install.sh 的 install_weixin_plugin() 逻辑同源：
# 读 openclaw-weixin.version.json 的 pin，走 npmmirror 在线 plugins install。
# 预装后首启只需扫码绑定，不必再装插件本体。
# config template 已预置 channels.openclaw-weixin.enabled + plugins.entries.openclaw-weixin.enabled，
# 但运行时 plugin 本体要 plugins install 才有，故这里预装。
install_weixin_plugin() {
    local claw_cmd="$PROJECT_ROOT/openclaw/openclaw.mjs"
    local node_bin="$PROJECT_ROOT/openclaw/node_modules/.bin/node"
    # 容器内用系统 node 跑 openclaw.mjs（apply-addons 已 pnpm install + build，dist 可直接跑）
    local node_run="node"
    local pin_file="$PROJECT_ROOT/openclaw-weixin.version.json"
    local pkg ver
    if [ -f "$pin_file" ]; then
        pkg=$(python3 -c "import json;print(json.load(open('$pin_file'))['openclaw-weixin']['package'])" 2>/dev/null || true)
        ver=$(python3 -c "import json;print(json.load(open('$pin_file'))['openclaw-weixin']['version'])" 2>/dev/null || true)
    fi
    pkg="${pkg:-@tencent-weixin/openclaw-weixin}"
    ver="${ver:-2.4.6}"
    # 幂等检查
    if (cd "$PROJECT_ROOT/openclaw" && npm_config_registry=https://registry.npmmirror.com pnpm openclaw plugins list 2>/dev/null | grep -q "openclaw-weixin"); then
        echo "[docker-bootstrap] openclaw-weixin plugin already installed"
        return 0
    fi
    echo "[docker-bootstrap] installing openclaw-weixin plugin (${pkg}@${ver}) via npmmirror"
    if (cd "$PROJECT_ROOT/openclaw" && npm_config_registry=https://registry.npmmirror.com pnpm openclaw plugins install "${pkg}@${ver}" --pin 2>/dev/null); then
        echo "[docker-bootstrap] openclaw-weixin plugin installed"
    else
        echo "[docker-bootstrap] ⚠️ openclaw-weixin 插件预装失败；首启可手动：pnpm openclaw plugins install ${pkg}@${ver} --pin"
    fi
}
install_weixin_plugin

# ─── gateway 配置：bind lan + token mode（token 由 entrypoint 首启生成）─────
# 容器内 gateway 要经 published localhost:18789 端口被宿主访问，故 bind lan（非 loopback）。
# token 不持久化进镜像（安全），entrypoint 首启生成随机 token 写 ~/.openclaw/.env。
OPENCLAW_CONFIG_PATH="$OPENCLAW_CONFIG_PATH" node - <<'NODE'
const fs = require('fs');
const path = process.env.OPENCLAW_CONFIG_PATH;
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
config.gateway = { ...(config.gateway || {}), bind: 'lan' };
config.gateway.auth = { ...(config.gateway.auth || {}), mode: 'token' };
delete config.gateway.auth.token;
fs.writeFileSync(path, `${JSON.stringify(config, null, 2)}\n`);
NODE

echo "[docker-bootstrap] ✅ immutable application layer prepared"
