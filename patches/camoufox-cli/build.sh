#!/bin/bash
# Build the wiseflow fork of camoufox-cli and install it globally,
# replacing any upstream `camoufox-cli` on $PATH.
#
# Run from anywhere:  patches/camoufox-cli/build.sh
# Re-run after editing fork source. Idempotent in effect.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "→ [camoufox-cli fork] installing deps (incl. devDeps for tsc)..."
# registry 走环境变量（容器构建时由 docker-bootstrap.sh export npm_config_registry 透传，
# 海外 arm64 runner override 成 npmjs 不跨境；裸机 install.sh 也 export 同名变量走 npmmirror）。
# 显式 --registry 兜底：npm install 不一定继承 npm_config_registry（npm CLI 版本差异），写死则跨架构炸。
REG="${npm_config_registry:-https://registry.npmmirror.com}"
npm install --registry="$REG"

echo "→ [camoufox-cli fork] building dist/..."
npm run build

echo "→ [camoufox-cli fork] installing globally (replaces upstream)..."
npm install -g .

echo "✅ forked camoufox-cli installed. Verify with:"
echo "    camoufox-cli --help 2>&1 | head   # should list upload / identity"
echo "    npm ls -g camoufox-cli            # version 0.6.2-wiseflow.1"
