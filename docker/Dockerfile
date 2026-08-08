# syntax=docker/dockerfile:1
# xiaobei Docker image — 开箱即用版（v5.6.3+）
#
# 三阶段构建：
#   1. xiaobei-build  基础系统 + Node/pnpm 工具链 + 容器内 Xvfb/VNC/noVNC 软件
#      + 跑 docker-bootstrap.sh 完成"install.sh 装好后"的所有 immutable 层
#      （apply patches / 装 skills+deps / 编译 openclaw / camoufox-cli+Firefox /
#       预装 openclaw-weixin 插件 / 生成 runtime seed）
#   2. xiaobei-runtime  从 build 拷贝产物，只放可执行层 + entrypoint，体积更瘦
#
# 镜像语义：等价于裸机跑完 scripts/install.sh 后的状态——用户只需 docker compose up -d
# 即可启动，唯一要填的 AWK_API_KEY 走环境变量注入，不进镜像层。
#
# openclaw/ 源码树（含 .git 元数据）由 build-image.sh 或 CI 流水线在 docker build 之前
# 注入到仓根，apply-addons.sh 的 git apply --3way 需 .git object store 读补丁头 pre-image blob。

# ════════════════════════════════════════════════════════════════════
# Stage 1: build（装齐 immutable 应用层 + 显示栈软件）
# ════════════════════════════════════════════════════════════════════
FROM node:24-bookworm AS xiaobei-build

ARG USE_MIRROR=1
ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/root \
    OPENCLAW_HOME=/root/.openclaw \
    OPENCLAW_STATE_DIR=/root/.openclaw \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

# 国内镜像加速（USE_MIRROR=0 关闭，海外构建用）
RUN if [ "$USE_MIRROR" = "1" ]; then \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
        || sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true; \
    fi

# 基础工具 + 显示栈（camoufox 有头模式跑 Xvfb，用户经 noVNC 操作浏览器过验证）
# + 浏览器运行时依赖（gtk/dbus/nss/atspi/cups，camoufox Firefox 需要）
# + 微信容器配合：docker CLI 让 xiaobei 容器能 docker exec 进微信容器读消息库
# 合并成一次 apt-get 减层数
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git openssl openssh-client \
        python3 python3-pip python3-venv \
        # 显示栈
        xvfb fluxbox x11vnc novnc websockify \
        # 浏览器运行时（camoufox Firefox）
        libasound2 libdbus-1-3 libgtk-3-0 libxt6 libxkbcommon-x11-0 \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libgbm1 libpango-1.0-0 libcairo2 libatspi2.0-0 \
        fonts-liberation fonts-noto-cjk fonts-wqy-microhei \
        # 微信容器配合（wx-mp-hunter posts-list 用 docker exec 读消息库）
        docker.io \
        # 杂项
        sudo procps net-tools \
    && rm -rf /var/lib/apt/lists/*

# pnpm via corepack（node:24 带 corepack）
RUN corepack enable && corepack prepare pnpm@10.30.2 --activate

WORKDIR /opt/xiaobei

# 仓根整体 COPY（.dockerignore 排除 node_modules/dist/.git，但保留 openclaw/.git）
# docker-bootstrap.sh 在仓根 docker/ 下，apply-addons.sh / setup-crew.sh 在 scripts/ 下，
# camoufox-cli fork 在 patches/camoufox-cli/ 下，全部随仓根打进镜像。
COPY . /opt/xiaobei

# 校验源码树 + 跑 bootstrap 完成"装好后"状态
# bootstrap 复用裸机安装的 apply-addons.sh / setup-crew.sh / camoufox-cli/build.sh，
# 但不跑 daemon install / 不交互收密钥 / 不拉远程仓库（源码已 COPY 进来）
RUN test -d /opt/xiaobei/openclaw \
    && test -d /opt/xiaobei/openclaw/.git \
    && test -x /opt/xiaobei/docker/docker-bootstrap.sh \
    && NODE_OPTIONS="--max-old-space-size=4096" /opt/xiaobei/docker/docker-bootstrap.sh \
    && install -d /opt/xiaobei/runtime-seed/openclaw \
    && cp -a /root/.openclaw/. /opt/xiaobei/runtime-seed/openclaw/

# ════════════════════════════════════════════════════════════════════
# Stage 2: runtime（瘦运行镜像，从 build 拷 immutable 层）
# ════════════════════════════════════════════════════════════════════
FROM node:24-bookworm

ARG USE_MIRROR=1
ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/root \
    OPENCLAW_HOME=/root/.openclaw \
    OPENCLAW_STATE_DIR=/root/.openclaw \
    DISPLAY=:99 \
    LANG=C.UTF-8

RUN if [ "$USE_MIRROR" = "1" ]; then \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
        || sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true; \
    fi

# runtime 只装显示栈 + 浏览器运行时 + docker CLI（不带构建工具链，瘦镜像）
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl openssl \
        python3 python3-pip \
        xvfb fluxbox x11vnc novnc websockify \
        libasound2 libdbus-1-3 libgtk-3-0 libxt6 libxkbcommon-x11-0 \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libgbm1 libpango-1.0-0 libcairo2 libatspi2.0-0 \
        fonts-liberation fonts-noto-cjk fonts-wqy-microhei \
        docker.io \
        procps net-tools \
    && rm -rf /var/lib/apt/lists/*

# 从 build 阶段拷贝 immutable 应用层
# /opt/xiaobei       仓根（引擎源码+dist / patches / scripts / crews / skills / awada / camoufox-cli fork）
# /root/.openclaw    预装态（openclaw.json template / 全局 skills / crew workspaces / weixin 插件）
# /root/.camoufox-cli  Firefox 二进制 + camoufox-cli 全局包
# /usr/local         Node + pnpm（node:24 带，corepack pnpm 在 build 装的）
COPY --from=xiaobei-build /opt/xiaobei /opt/xiaobei
COPY --from=xiaobei-build /root/.openclaw /root/.openclaw
COPY --from=xiaobei-build /root/.camoufox-cli /root/.camoufox-cli
COPY --from=xiaobei-build /root/.cargo /root/.cargo
# camoufox-cli 全局 npm 包（build 阶段 npm install -g 装的）
COPY --from=xiaobei-build /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=xiaobei-build /usr/local/bin /usr/local/bin.d-build
# 把 build 阶段的全局 bin（camoufox-cli 等）合并到 runtime 的 /usr/local/bin
RUN cp -a /usr/local/bin.d-build/* /usr/local/bin/ 2>/dev/null || true && rm -rf /usr/local/bin.d-build

# pnpm 在 runtime 也需要（openclaw gateway 用 pnpm openclaw gateway 启动）
RUN corepack enable && corepack prepare pnpm@10.30.2 --activate

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/xiaobei-entrypoint
RUN chmod 0755 /usr/local/bin/xiaobei-entrypoint

# 两个数据目录外挂——首启从镜像内 runtime-seed 初始化空卷，已有卷绝不覆盖
# 两个目录含 API key 和平台登录态，权限 0700
VOLUME ["/root/.openclaw", "/root/.camoufox-cli"]

# gateway API + noVNC web
EXPOSE 18789 6080

ENTRYPOINT ["/usr/local/bin/xiaobei-entrypoint"]
