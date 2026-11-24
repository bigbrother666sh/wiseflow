# wiseflow 安装排障

> 配套 `scripts/install.sh`（curl 一键首装）与 `scripts/update.sh`（升级）。
>
> **两个路径，别混淆**：
> - `~/xiaobei/` = wiseflow 源码 checkout 目录（install.sh clone 的目标，含 `openclaw/` 上游子仓 + `patches/` + `crews/` + `skills/` + `awada/` + `scripts/`，仓内结构保持完整，由软链注入到运行态）
> - `~/.openclaw/` = openclaw 运行态 home（`openclaw.json`、`daemon.env`、`workspaces/`、`sessions/`、camoufox-cli profile、`skills/` 软链目标都在此）
>
> 排障前先确认这两个目录的存在与结构：
> `ls ~/xiaobei/{openclaw,patches,crews,skills,scripts} && ls ~/.openclaw/{openclaw.json,.env,daemon.env,workspaces,skills}`

## 运行日志

默认日志级别为 `warn`，保留警告、错误和致命故障，日常模型请求、连接状态和成功投递不写入。主日志位于 `~/.openclaw/logs/gateway.log`，每行一条 JSON；由 OpenClaw 原生按 10 MiB 大小轮转，保留五份编号备份。Docker 中位于持久化的 `/root/.openclaw/logs/`。安装和更新只补缺少的日志配置，保留用户显式设置的级别、路径与轮转大小。

本节中的 `openclaw` 指当前安装的 CLI 入口。只有入口已加入终端 PATH 时，才能在任意目录直接敲 `openclaw`；服务的 PATH 配置不等于终端的 PATH。按实际安装目录选择下面的一条独立命令：

| 安装方式 / 终端 | 查看最近 20 行，不跟随 |
| --- | --- |
| 已有 CLI 在 PATH（各平台） | `openclaw logs --limit 20` |
| macOS / Linux 预构建安装（默认目录） | `~/xiaobei/bin/openclaw logs --limit 20` |
| Windows 原生预构建安装，PowerShell | `& "$env:USERPROFILE\xiaobei\bin\openclaw.cmd" logs --limit 20` |
| 源码部署，使用已构建引擎（按实际项目目录替换） | `node "/实际项目目录/openclaw/dist/index.js" logs --limit 20` |

WSL 使用 WSL 内的 Linux 入口，不把 Windows 原生安装与 WSL 路径混用。源码的 `pnpm openclaw` 支持相同日志参数，但可能触发构建，运行中的 Gateway 排障使用已安装入口或已构建 CLI。

需要更多记录时使用 `openclaw logs --limit 200 --plain`；交互持续查看使用 `openclaw logs --follow`。自动巡检使用有界的 `--limit`，不无限跟随。Gateway 不可达时可以直接读取实际日志文件；Linux 服务启动和退出记录用 `journalctl --user -u openclaw-gateway.service -n 100 --no-pager` 查看，macOS / Windows / 容器内不使用该命令。旧机器若仍有 `StandardOutput` / `StandardError` 文件重定向，以实际 systemd drop-in 为准，先核实依赖该文件的监控再迁移。不要把参考源码目录 `wiseflow-pro/` 作为新的运行日志目录。

需要复现和排查正常流程时，可临时运行 `openclaw config set logging.level '"info"' --strict-json`；需要更细信息时设为 `debug`，完成后恢复 `warn`。这些原生日志配置可热更新；console 输出单独由 `logging.consoleLevel` 控制。不要用 `silent` 或删除错误日志来消除告警。

日志汇总时，单纯的 `memory pressure: level=warning reason=rss_threshold` 属于内存观察项；结合主机可用内存、连续运行趋势判断。持续增长、`critical`、OOM、事件循环阻塞和任务失败仍须核查，不因默认降噪而忽略。

## 常见症状 → 速查表

| 现象 | 速断 | 修复 |
|------|------|------|
| `bash: pnpm: command not found` 装好后新开 shell 才报 | corepack 装的 pnpm 路径未在 PATH | `corepack enable` 或 `npm install -g pnpm@11.2.2`，新开 shell 验证 |
| `node: v18.x.x` 装好但版本低于 22.19 | 系统 node 太旧，install.sh 装的新版未生效 | mac: `brew link --overwrite --force node@24`；Linux: 检查 nvm/nodenv 当前版本，或 `source ~/.nvm/nvm.sh && nvm use 24` |
| `openclaw: command not found` | 当前安装的 CLI 未在终端 PATH | 使用上方平台入口；源码部署使用已构建的 dist/index.js，不为查日志额外安装可能版本不匹配的全局 CLI |
| onboard 报 `Non-interactive setup requires explicit risk acknowledgement` | 在 CI/无 TTY 跑 onboard 没加 `--accept-risk` | 加 `--non-interactive --accept-risk`，且补全所有 `--auth-choice` / `--custom-api-key` 等必填 flag |
| onboard `--skip-channels` 后 channel 段仍问 | openclaw 版本低于本仓 `openclaw.version` 锁的 commit | `cd ~/xiaobei && ./scripts/update.sh` 重 checkout + build |
| 预构建安装报 `ERR_PNPM_OUTDATED_LOCKFILE`，指向 `extensions/browser`，或提示缺少 `packages/speech-core` importer | 程序目录中的旧工作区残留，与新锁文件冲突 | 按下方“预构建升级的依赖冲突”备份程序目录后重跑安装；保留 `--frozen-lockfile` |
| 安装技能依赖时 `ui-demo` 报私有 `playwright-core` 依赖 | 已删除的旧 `package.json` 残留；当前 `ui-demo` 不再有该文件 | 按下方步骤备份整个程序目录后重装，不补装私有 Playwright |
| `pnpm build` 报 `tsc: error TS2307: Cannot find module '...'` | patch 未应用或应用不完整 | `cd ~/xiaobei && bash scripts/apply-addons.sh --force` 重跑 patches |
| gateway 启动报 `EADDRINUSE 0.0.0.0:18789` | 端口被占（旧 gateway 没退干净） | `lsof -i :18789` 找进程，`kill -9 <pid>`；或改 `~/xiaobei/openclaw/package.json` 的 gateway 默认端口 |
| gateway 启动报 `OPENCLAW_GATEWAY_TOKEN missing` | 首次启动未生成 token | `cd ~/xiaobei/openclaw && pnpm openclaw gateway install --force` 重装会生成；或手动设 env |
| camoufox-cli install 卡在 Firefox 下载（557MB） | 网慢 | 等即可；卡半小时以上重跑 `camoufox-cli install`（幂等） |
| WSL2 下浏览器无头报 `DISPLAY not set` | install.sh 的 WSL 棵测没生效 | 手动 `export DISPLAY=:0 WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir`，重启 gateway |
| agent 跑任务报 `skill script not executable` | setup-crew.sh 的 chmod 段被跳过 | `cd ~/xiaobei && bash scripts/setup-crew.sh` 重跑（幂等） |
| agent 报 `escaped skill path` warning | skill 软链 target 未在 `skills.load.allowSymlinkTargets` | `cd ~/xiaobei && bash scripts/apply-addons.sh` 重跑（setup-crew.sh 会注入） |

## 分段排障

### 更新安装脚本与复用旧 tarball

远程安装入口和安装包内的脚本分别更新。通过 `curl .../master/scripts/install.sh | bash` 或 `irm .../master/scripts/install.ps1 | iex` 获取并执行新版入口时，入口中的系统依赖准备、下载、解压替换等逻辑可直接配合原有 5.8.2 tarball 使用，不要求更新产品版本号或重建引擎。

解压后执行的 `scripts/python-runtime.mjs`、`scripts/install-browser.mjs`、`scripts/install-skill-deps.mjs`、`scripts/setup-crew.sh` 和 `crews/main/skills/platform-runtime/scripts/install-runtime.mjs` 等文件来自 tarball。当前入口不会自动从仓库同步这些文件；只更新 Git 仓库不能让旧包获得相应修复，手动覆盖的文件也可能在下次解压时被旧包覆盖。直接运行本机已有的安装入口同样不会自动更新它自己。

若要保持 tarball 完全不变，同时应用包内脚本修复，需要另行提供并验证解压后的修复文件同步流程。仅保持版本号不变、允许重建安装包时，可用 Build Dist Tarball 的 `tag=v5.8.2` 和 `source_ref=<包含修复的提交>` 维护重建；工作流修改只影响新构建，不改变现有 release 文件或用户下载缓存。普通安装入口指向的正式仓库及 AtomGit 镜像也需要同步对应入口变更，开发仓推送不会自动替代这些地址的内容。

### 预构建升级的依赖冲突

若报错出现 `extensions/browser` 的依赖差异、锁文件缺少 `importers["packages/speech-core"]`，或 `ui-demo` 声明私有 `playwright-core`，通常是覆盖解压留下了旧版程序文件。已删除的引擎包和技能依赖声明仍会被安装器发现。当前 `ui-demo` 没有 `package.json`。Ubuntu、macOS 和 Windows 的重复安装都可能遇到。

新版安装器会先移开程序目录中的 `bin`、`openclaw`、`browser`、`crews`、`skills`、`awada`、`scripts` 和 `config-templates`，再解压新程序；解压和必要文件校验失败时恢复这些目录，成功后删除临时旧副本。`tools` 中的自管 Python 和浏览器下载缓存 `browser/.browsers` 保留。Git 源码 checkout 或上述目录的链接会阻止替换，请改用独立的 `XIAOBEI_HOME`。运行包还会移除仅编译需要的插件工作区条目。

使用旧安装器的 Windows 用户可先在 PowerShell 备份整个程序目录，成功后重跑原安装命令。这样可以同时隔离引擎和技能中的残留。无需删除用户 home 下的 `.openclaw` 或重新下载安装包：

```powershell
$xiaobeiDir = if ($env:XIAOBEI_HOME) { $env:XIAOBEI_HOME } else { Join-Path $env:USERPROFILE 'xiaobei' }
Move-Item -LiteralPath $xiaobeiDir -Destination ($xiaobeiDir + '-backup-' + [Guid]::NewGuid().ToString('N')) -ErrorAction Stop -PassThru
```

此命令将整个程序目录移到同级备份，备份会保留；不改写用户 home 下 `.openclaw` 中的配置、账号、会话和工作区。若将 `OPENCLAW_HOME` 自定义在程序目录内，先把它迁出并更新该变量，再进行此操作。只清理插件或引擎无法清除 crew 技能中的残留。不要使用 `--no-frozen-lockfile`、重新生成锁文件或允许技能私装 Playwright 来绕过问题。自定义了安装路径但未保留 `XIAOBEI_HOME` 时，请将第一行改为实际程序目录。

### platform-runtime 安装失败

`Skill dependency install failed: ...platform-runtime` 是汇总提示。保留其前面的 npm 或 `Prepared platform runtime cannot load on this machine` 错误，按实际异常修复。不要仅根据汇总提示重复清空程序目录。

需要单独复现并取得完整错误时，在 PowerShell 只重跑该组件的安装器：

```powershell
$xiaobeiDir = if ($env:XIAOBEI_HOME) { $env:XIAOBEI_HOME } else { Join-Path $env:USERPROFILE 'xiaobei' }
$env:PATH = (Join-Path $xiaobeiDir 'tools\node') + ';' + $env:PATH
& "$xiaobeiDir\tools\node\node.exe" "$xiaobeiDir\crews\main\skills\platform-runtime\scripts\install-runtime.mjs" --npm-cli "$xiaobeiDir\tools\node\node_modules\npm\bin\npm-cli.js" --registry https://registry.npmmirror.com
```

若原始错误为 `ERR_UNSUPPORTED_ESM_URL_SCHEME` / `Received protocol 'c:'`，检查运行包安装自检是否把 Windows 绝对路径直接传给了 ESM `import()`。平台入口和 `require.resolve('wreq-js')` 的结果均需先用 `pathToFileURL()` 转换。保留包完整性、范围与依赖校验，不跳过自检。安装成功后的 `--check` 失败时，共享技能安装器应显示原始异常，并保留未更新的成功标记。

### 1. Node / pnpm / git 未就绪

install.sh 在 macOS 走 `brew install node@24`，Linux 走 NodeSource 官方脚本。如果失败：

```bash
# 手动验装
node -v   # 应 ≥ v22.19
pnpm --version  # 应为 11.2.2
git --version
```

- **mac brew 装失败**：先 `xcode-select --install` 装 CLT，再 `brew install node@24`
- **Linux NodeSource 失败**：手动加 repo：`curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash - && sudo apt-get install -y nodejs`
- **pnpm 缺**：`npm install -g pnpm@11.2.2`（不走 corepack 的回退）

### 2. clone / checkout 段失败

```bash
ls ~/xiaobei/.git                # 应存在
git -C ~/xiaobei rev-parse HEAD  # 应有 commit hash
ls ~/xiaobei/openclaw/.git       # 应存在
source ~/xiaobei/openclaw.version
git -C ~/xiaobei/openclaw rev-parse HEAD  # 应等于 $OPENCLAW_COMMIT
```

- **clone wiseflow 失败**：网问题或 GitHub 限速，`git clone https://github.com/TeamWiseFlow/xiaobei.git ~/xiaobei` 重试；或用 atomgit 镜像 `https://atomgit.com/wiseflow/xiaobei.git`
- **checkout openclaw@pin 失败**：`git -C ~/xiaobei/openclaw fetch --unshallow origin` 深化历史后重试

### 3. apply-addons 段失败

apply-addons.sh 是 patches + skills + crew 模板 + awada + Python/npm deps 的总安装段，失败时通常报在 patch 应用：

```bash
cd ~/xiaobei
bash scripts/apply-addons.sh --force  # --force 重跑覆盖
```

常见 patch 失败原因：`openclaw/` 子目录漂移到非 `openclaw.version` 锁的 commit。修复：

```bash
cd ~/xiaobei/openclaw
git fetch origin
git checkout "$(source ~/xiaobei/openclaw.version && echo $OPENCLAW_COMMIT)"
git reset --hard HEAD
git clean -fd
cd ~/xiaobei
bash scripts/apply-addons.sh --force
```

### 4. pnpm build 段失败

openclaw 是大 monorepo，build 偶发 OOM。Node 默认 heap 4GB，build 段可显式抬：

```bash
cd ~/xiaobei/openclaw
NODE_OPTIONS="--max-old-space-size=8192" pnpm build
```

`pnpm ui:build` 失败无害（CLI 不依赖 UI），可跳：

```bash
pnpm build  # 跑通即可
# pnpm ui:build 失败不影响 CLI
```

### 5. camoufox-cli 段失败

- **`npm install -g camoufox-cli` 失败**：网或 npm registry 问题，`npm config set registry https://registry.npmmirror.com` 切国内镜像后重试
- **`camoufox-cli install` 失败**：Firefox 二进制下载问题，`camoufox-cli install --verbose` 看具体错误；也可手动从 [camoufox releases](https://github.com/daijro/camoufox/releases) 下对应 arch 包到 `~/.camoufox-cli/`

### 6. onboard 段失败

onboard 是唯一交互段（问模型供应商 + API key）。失败常见：

- **无 TTY**（CI / curl | bash 路线）：install.sh 已检测并 fallback 到提示用户手动跑。如要在 CI 跑：`pnpm openclaw onboard --non-interactive --accept-risk --auth-choice custom-api-key --custom-api-key <key> --custom-base-url <url> --custom-model-id <id> --skip-channels --skip-skills --skip-bootstrap --skip-health --skip-ui --install-daemon`
- **auth-choice 不认**：跑 `pnpm openclaw onboard --help` 看当前版本支持的 choice 列表（不同 openclaw 版本字段有差异）
- **daemon install 段失败**：mac 看 `~/Library/LaunchAgents/ai.openclaw.gateway.plist` 是否生成；Linux 看 `~/.config/systemd/user/openclaw-gateway.service` 是否生成。手动重装：`pnpm openclaw daemon uninstall && pnpm openclaw daemon install`

### 7. gateway 起不来

```bash
~/xiaobei/bin/openclaw gateway status --deep  # 深探
~/xiaobei/bin/openclaw logs --limit 200 --plain  # 查看最近日志
```

常见：

- **`OPENCLAW_GATEWAY_TOKEN missing`**：首装时未生成。`pnpm openclaw gateway install --force` 重装会生成；或手动 `openssl rand -hex 32` 生成写入 `~/.openclaw/.env` 的 `OPENCLAW_GATEWAY_TOKEN=`
- **端口被占**：`lsof -i :18789` 找旧进程 kill；或改 `~/.openclaw/openclaw.json` 的 `gateway.port`
- **mac launchd 不自启**：`launchctl list | grep openclaw` 看状态；`launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway` 重启
- **Linux systemd 不自启**：`systemctl --user status openclaw-gateway`；`systemctl --user daemon-reload && systemctl --user restart openclaw-gateway`

## 升级后异常

`update.sh` 走 reload + restart 不卸装 daemon，但偶发 dist 残留旧文件导致行为异常：

```bash
cd ~/xiaobei
bash scripts/apply-addons.sh --force   # 重跑 patches + setup
cd openclaw
pnpm build
pnpm openclaw daemon restart
```

如仍异常，核弹选项（保留 `~/.openclaw` 用户态，重 build 引擎）：

```bash
cd ~/xiaobei/openclaw
git reset --hard HEAD
git clean -fd
cd ~/xiaobei
bash scripts/apply-addons.sh --force
cd openclaw && pnpm build
pnpm openclaw daemon restart
```

## 重置回到出厂

**保留 wiseflow 源码**，只重置 openclaw 运行态：

```bash
# 备份当前 openclaw.json + .env（含 API key 与 channel 绑定）
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
cp ~/.openclaw/.env ~/.openclaw/.env.bak

# 走 openclaw onboard 的 reset
cd ~/xiaobei/openclaw
pnpm openclaw onboard --reset --reset-scope config
# 会清 config 但保留 creds + sessions；若要全清用 --reset-scope full
```

**全重置（连 channel 绑定都清）**：

```bash
rm -rf ~/.openclaw
cd ~/xiaobei
bash scripts/apply-addons.sh --force   # 重建 openclaw.json + workspaces
cd openclaw
pnpm openclaw onboard --skip-channels --skip-skills --skip-bootstrap --skip-health --skip-ui --install-daemon
```

## 还是不行

按以下顺序收集信息后提 [issue](https://github.com/TeamWiseFlow/xiaobei/issues)：

1. `node -v && pnpm --version && git --version`
2. `source ~/xiaobei/openclaw.version && echo "OPENCLAW_VERSION=$OPENCLAW_VERSION OPENCLAW_COMMIT=$OPENCLAW_COMMIT"`
3. `git -C ~/xiaobei/openclaw rev-parse HEAD`
4. `pnpm openclaw --version`（在 `~/xiaobei/openclaw` 下跑）
5. `pnpm openclaw doctor --non-interactive` 的完整输出
6. 失败段的完整 stderr（`bash scripts/install.sh --verbose` 重跑抓输出）

提 issue 时把这 6 项贴全，能显著缩短回环时间。

---

🎉 xiaobei 项目目前提供 **VIP Club**（售价 **168 元/年**），权益包括：

- **付费知识库**：包含《手把手从零开始安装教程》、《安装之后三分钟上手指南》、《Openclaw 自定义配置全案教程》、《Windows 下安装 WSL2 无脑教程》以及各种最佳实践分享
- **vip 微信交流群**，共同探讨交流各种自动化获客玩法，搞钱路上不孤单
- 免费加入 Wiseflow 知识星球
- 每月一次的线上闭门分享（腾讯会议），陪伴你从"小白"到"大神"！
- **会员有效期内免费使用官方中转服务**：涉及小红书、抖音、bili、快手、微信公众号、企业微信朋友圈的技能都需要固定IP（平台要求），一般的家庭网络或办公网络环境并没有固定IP，Wiseflow团队已经搭建了官方的中转服务，vipclub会员期内畅用，不必再单独自建或购买。

此外，我们也面向 VIP Club 会员提供如下增值服务：**远程安装部署、远程技术支持、awada lane 租赁** (需额外付费）

欢迎添加"掌柜的"企业微信（这背后接的就是 xiaobei sales-cs）咨询了解：

<img width="360" height="360" alt="xiaobei掌柜" src="https://github.com/user-attachments/assets/b013b3fd-546e-4176-b418-57bee419e761" />

🌹 开源不易，感谢支持！
