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
#
# 诊断：每步打 [bootstrap] STEP N done 标记，ACR 构建失败时精确定位哪步炸。
# 容错：非致命步骤（camoufox 二进制、weixin 插件）失败不中断构建——首启可手动补。
set -uo pipefail  # 不用 -e：用显式 || exit 1 控制致命步，非致命步容错

PROJECT_ROOT="${XIAOBEI_ROOT:-/opt/xiaobei}"
OPENCLAW_HOME="${OPENCLAW_HOME:-/root/.openclaw}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_HOME/openclaw.json}"

# USE_MIRROR=0（阿里云 ACR 海外构建机）走原始 npmjs + ACR 海外源智能加速
# USE_MIRROR=1（国内本地构建）走 npmmirror
if [ "${USE_MIRROR:-1}" = "0" ]; then
  export NPM_REGISTRY="https://registry.npmjs.org"
  export npm_config_registry="https://registry.npmjs.org"
else
  export NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
  export npm_config_registry="${NPM_REGISTRY}"
fi
echo "[bootstrap] NPM_REGISTRY=${NPM_REGISTRY} USE_MIRROR=${USE_MIRROR:-1}"

# ─── 校验源码树（致命）────────────────────────────────────────────
[ -d "$PROJECT_ROOT/openclaw/.git" ] || { echo "[bootstrap] ❌ openclaw 源码树缺 .git" >&2; exit 1; }
[ -x "$PROJECT_ROOT/scripts/apply-addons.sh" ] || { echo "[bootstrap] ❌ apply-addons.sh 缺失" >&2; exit 1; }

mkdir -p "$OPENCLAW_HOME"

# ─── 放置 config template ────────────────────────────────────────
cp "$PROJECT_ROOT/config-templates/openclaw.json" "$OPENCLAW_CONFIG_PATH"
cp "$PROJECT_ROOT/config/daemon.env.template" "$OPENCLAW_HOME/daemon.env"
cp "$PROJECT_ROOT/config/.env.template" "$OPENCLAW_HOME/.env"
chmod 600 "$OPENCLAW_HOME/daemon.env" "$OPENCLAW_HOME/.env"

# template 内 ${XIAOBEI_HOME} 解析成容器内固定路径写回
node -e '
    const fs = require("fs");
    const p = process.argv[1];
    let raw = fs.readFileSync(p, "utf8");
    raw = raw.replace(/\$\{XIAOBEI_HOME\}/g, "/opt/xiaobei");
    fs.writeFileSync(p, raw);
' "$OPENCLAW_CONFIG_PATH"
echo "[bootstrap] STEP 1 done: config template placed"

# ─── camoufox-cli fork 构建 + 全局安装（致命：browser-guide 依赖）────
echo "[bootstrap] STEP 2: building camoufox-cli fork..."
if ! "$PROJECT_ROOT/patches/camoufox-cli/build.sh"; then
  echo "[bootstrap] ❌ camoufox-cli build failed" >&2
  exit 1
fi
echo "[bootstrap] STEP 2 done: camoufox-cli fork built + installed globally"

# ─── apply-addons：patch + skills + crew + 编译（致命）────────────
echo "[bootstrap] STEP 3: applying addons (patches + skills + crews + build)..."
if ! "$PROJECT_ROOT/scripts/apply-addons.sh" --force --no-restart; then
  echo "[bootstrap] ❌ apply-addons.sh failed" >&2
  exit 1
fi
echo "[bootstrap] STEP 3 done: addons applied + openclaw built"

# ─── camoufox-cli install：拉 Firefox 二进制（非致命，首启可补）────
# 幂等：已装且版本一致时打印 "already up to date" 并返回
echo "[bootstrap] STEP 4: ensuring camoufox Firefox binary..."
camoufox-cli install || echo "[bootstrap] ⚠️ camoufox-cli install failed（可后续手动 camoufox-cli install）"
echo "[bootstrap] STEP 4 done"

# ─── 预装 openclaw-weixin 插件（非致命，首启可补）────────────────
# 与裸机 install.sh 的 install_weixin_plugin() 同源：读 pin 走在线 plugins install
install_weixin_plugin() {
    local pin_file="$PROJECT_ROOT/openclaw-weixin.version.json"
    local pkg ver
    if [ -f "$pin_file" ]; then
        pkg=$(python3 -c "import json;print(json.load(open('$pin_file'))['openclaw-weixin']['package'])" 2>/dev/null || true)
        ver=$(python3 -c "import json;print(json.load(open('$pin_file'))['openclaw-weixin']['version'])" 2>/dev/null || true)
    fi
    pkg="${pkg:-@tencent-weixin/openclaw-weixin}"
    ver="${ver:-2.4.6}"
    # 幂等检查
    if (cd "$PROJECT_ROOT/openclaw" && pnpm openclaw plugins list 2>/dev/null | grep -q "openclaw-weixin"); then
        echo "[bootstrap] openclaw-weixin plugin already installed"
        return 0
    fi
    echo "[bootstrap] installing openclaw-weixin plugin (${pkg}@${ver})"
    if (cd "$PROJECT_ROOT/openclaw" && pnpm openclaw plugins install "${pkg}@${ver}" --pin); then
        echo "[bootstrap] openclaw-weixin plugin installed"
    else
        echo "[bootstrap] ⚠️ openclaw-weixin 插件预装失败；首启可手动：pnpm openclaw plugins install ${pkg}@${ver} --pin"
    fi
}
echo "[bootstrap] STEP 5: installing openclaw-weixin plugin..."
install_weixin_plugin
echo "[bootstrap] STEP 5 done"

# ─── gateway 配置：bind lan + token mode ─────────────────────────
# 容器内 gateway 要经 published localhost:18789 端口被宿主访问，故 bind lan
# token 不持久化进镜像，entrypoint 首启生成随机 token 写 ~/.openclaw/.env
OPENCLAW_CONFIG_PATH="$OPENCLAW_CONFIG_PATH" node - <<'NODE'
const fs = require('fs');
const path = process.env.OPENCLAW_CONFIG_PATH;
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
config.gateway = { ...(config.gateway || {}), bind: 'lan' };
config.gateway.auth = { ...(config.gateway.auth || {}), mode: 'token' };
delete config.gateway.auth.token;
fs.writeFileSync(path, `${JSON.stringify(config, null, 2)}\n`);
NODE
echo "[bootstrap] STEP 6 done: gateway config (bind lan + token mode)"

echo "[bootstrap] ✅ immutable application layer prepared"
