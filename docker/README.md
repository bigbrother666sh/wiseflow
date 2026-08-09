# xiaobei Docker 部署（v5.6.3+）

> **开箱即用**：镜像内已装好 openclaw 引擎 + 全部 skills/crews + camoufox-cli + Firefox +
> openclaw-weixin 插件 + Xvfb/fluxbox/x11vnc/websockify/noVNC 显示栈。
> 用户拉镜像后只需填 `AWK_API_KEY`，`docker compose up -d` 即可启动。

## 快速开始

```bash
# 1. 拷贝环境模板
cp docker/.env.example docker/.env

# 2. 编辑 .env，填入你的 AWK_API_KEY（阿里云百炼 token）
#    AWK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 3. 启动
docker compose up -d

# 4. 访问
#    gateway API:   http://localhost:18789
#    noVNC web:      http://localhost:6080/vnc.html
```

首启会打印微信扫码绑定二维码，用手机微信扫码确认登录即可。绑定态持久化在
`xiaobei-openclaw` 卷，后续重启自动跳过扫码。

## 镜像内容（= 跑完 install.sh 后的状态）

| 层 | 内容 |
|----|------|
| openclaw 引擎 | 按 `openclaw.version` pin 的 commit + 全部 patches + 编译后的 dist |
| awada 插件 | 本地 TS 插件 + ws/zod 运行时依赖 |
| skills | 公共 skills（`skills/`）+ crew 专属 skills（`crews/*/skills/`）+ python deps |
| crews workspace | main / content-producer / it-engineer / sales-cs 四套 crew 预初始化 |
| camoufox-cli | wiseflow fork（反指纹浏览器 CLI）+ Firefox 二进制（~557MB） |
| openclaw-weixin | 预装微信 channel 插件（首启扫码绑定） |
| 显示栈 | Xvfb（虚拟显示）+ fluxbox（窗口管理）+ x11vnc + websockify + noVNC |

**不装**：systemd/launchd daemon（容器无服务管理器）、交互式密钥收集（走环境变量）。

## 数据外挂（两个 named volume）

| Volume | 容器路径 | 内容 |
|--------|---------|------|
| `xiaobei-openclaw` | `/root/.openclaw` | openclaw.json、`.env`、workspace、会话、微信登录态 |
| `xiaobei-camoufox` | `/root/.camoufox-cli` | 浏览器 profile、Cookie、指纹缓存 |

**首启行为**：空卷从镜像内 `/opt/xiaobei/runtime-seed/openclaw` 初始化。
**升级行为**：已有卷**绝不覆盖**，登录态和用户配置保留。
**备份**：两个卷含 API key 和平台登录态，备份时应限制文件权限。
**清空**：`docker compose down -v` 删除卷，等同于清空该实例的配置与登录状态。

## noVNC — 浏览器操作容器内桌面

camoufox 有头模式跑在容器内 Xvfb 虚拟显示里。用户浏览器打开
`http://localhost:6080/vnc.html` 即可看到该显示里的 fluxbox 桌面，里面能看到 camoufox
浏览器窗口——用于**小红书/抖音等平台登录过验证**的场景。

**mimicwx 容器**也有自己的 noVNC web（宿主端口 `6081`）：浏览器开
`http://localhost:6081/vnc.html` 操作微信客户端扫码登录。

**端口默认只绑 Docker host 的 `127.0.0.1`**。远程访问应走 SSH 隧道或显式配置代理，
不要直接把 6080 / 6081 暴露到公网。

## 微信容器配合（wx-mp-hunter posts-list）

`wx-mp-hunter` skill 的 `posts-list` 子命令依赖一个运行中的微信客户端容器
（MimicWX-Linux），通过 `docker exec` 进微信容器读 SQLCipher 加密的消息库。

`docker-compose.yml` 已配好两个容器在同一 `xiaobei-net` 网络里：

- `xiaobei` 容器挂载宿主 `/var/run/docker.sock`（只读），用于 `docker exec` 进微信容器
- `mimicwx` 容器跑微信客户端，登录态持久化在 `wechat-data` 卷
- 环境变量 `WX_BIZ_CONTAINER` / `WX_BIZ_USER_DIR` / `WX_BIZ_KEYS_FILE` 指向微信容器

**前提**：需要先有 `mimicwx` 镜像。如果只用到 `wx-mp-hunter` 的 `fetch` / `homepage`
子命令（不依赖微信容器），可以注释掉 `docker-compose.yml` 里的 `mimicwx` service。

## 构建与分发（GitHub + 阈里云 ACR 直绑）

镜像由阿里云 ACR 企业版**直绑 GitHub 仓库**自动构建并托管——不走外部流水线，
push tag 即触发 ACR 构建。

### 触发方式

1. **手动触发**：在阿里云 ACR 控制台 → `xiaobei` 仓库 → 构建规则 → 点"立即构建"
2. **push tag 自动触发**：`git push origin v5.6.3` 会自动触发 ACR 构建规则

### ACR 构建规则配置（一次性）

在 ACR 控制台为 `xiaobei` 仓库添加一条构建规则：

| 字段 | 配置 |
|------|------|
| 代码源 | GitHub（先在 ACR 绑定 GitHub 个人版账号） |
| 分支/Tag | 正则 `v(?<imageTag>\w*)` 匹配 `v*` tag |
| 构建上下文目录 | `/` |
| Dockerfile 文件名 | `docker/Dockerfile` |
| 镜像版本 | `${imageTag}` 和 `latest`（加两条镜像版本行，或建两条规则） |
| 海外机器构建 | **勾选**（构建机走海外链路拉 Docker Hub 基础镜像 `node:24-bookworm`，国内 Mirror 链路不稳会超时；Dockerfile 内的 npmmirror + 阿里云 APT 源是另一条链路，不冲突） |
| 构建参数 | 无（Dockerfile 已写死国内镜像源，不引入 USE_MIRROR 分支复杂度） |

### 产物（阿里云 ACR）

```
registry.cn-hangzhou.aliyuncs.com/<namespace>/xiaobei:v5.6.3
registry.cn-hangzhou.aliyuncs.com/<namespace>/xiaobei:latest
```

### 发放模式

构建完成后，向符合条件的用户直接发放阿里云的 image 链接：

```bash
# 用户侧：拉镜像 + 启动
docker login registry.cn-hangzhou.aliyuncs.com  # 填发放的账号
docker pull registry.cn-hangzhou.aliyuncs.com/<namespace>/xiaobei:v5.6.3
cp docker/.env.example docker/.env  # 填 AWK_API_KEY
AWK_API_KEY=<key> docker compose up -d
```

## 本地验证

```bash
# 本地构建镜像（会先按 openclaw.version 检出 pinned openclaw 源码）
./scripts/build-image.sh

# 用本地构建的镜像启动
AWK_API_KEY=<your-key> IMAGE=xiaobei:local docker compose up -d
```

## 安全边界

- `AWK_API_KEY` 仅从运行环境读取，**不写入镜像层**也不写 `openclaw.json` 的明文。
- 首启会为 gateway 生成随机 `OPENCLAW_GATEWAY_TOKEN`，以 `0600` 写入持久化 `.env`。
- Gateway 和 noVNC 在 Compose 中只映射到 `127.0.0.1`。**不要直接把 6080 暴露到公网**。
- 当前 Camoufox sandbox 需要 `SYS_ADMIN` capability；只运行受信任的官方镜像，并保持
  Docker daemon 权限最小化。
- `/var/run/docker.sock` 只读挂载——xiaobei 容器能 `docker exec` 进微信容器读消息库，
  但无法修改宿主 docker 状态。若需更强隔离，可改用 docker-socket-proxy。
