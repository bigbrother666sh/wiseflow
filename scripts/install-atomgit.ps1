# install-atomgit.ps1 - wiseflow 一键首装脚本（Windows，预构建 tarball 路线，atomgit 国内镜像专线）
#
# 与 install.ps1 区别：本脚本走 atomgit 国内镜像（tarball 走 atomgit.com → GitCode CDN，
#   tag 解析走 api.atomgit.com/api/v5），不经 GitHub；适合国内网络环境。
#   为对 `irm | iex` 友好（小白一条命令跑通），去掉 [CmdletBinding]param() 头，
#   所有可选参数走环境变量：
#     $env:XIAOBEI_HOME        程序目录覆盖（默认 ~\xiaobei）
#     $env:XIAOBEI_TAG         指定 release tag（默认拉最新）
#     $env:XIAOBEI_TARBALL     本地已下好的 tarball 路径，跳过下载
#     $env:XIAOBEI_FORCE       =1 强覆盖已有运行数据（~\.openclaw）
#     $env:XIAOBEI_SKIP_BIND   =1 跳过末尾微信扫码绑定
#     $env:XIAOBEI_SKIP_BROWSER=1 跳过 camoufox-cli 浏览器二进制（冒烟/CI）
#     $env:XIAOBEI_NO_PROMPT   =1 跳过所有交互提示（CI/自动化）
#
# 用法（PowerShell，需 Git Bash 或 WSL）：
#   irm https://raw.atomgit.com/wiseflow/xiaobei/raw/master/scripts/install-atomgit.ps1 | iex
#   # 或本地：
#   powershell -ExecutionPolicy Bypass -File install-atomgit.ps1
#
# ⚠️ 本文件必须保持 UTF-8 **带 BOM**：Windows PowerShell 5.1 对无 BOM 的 .ps1 按系统
#   ANSI 代码页（中文系统 GBK）解析，中文字符串会乱码并产生解析错误，脚本无法运行。
#
# 与 install.sh 同构（方案 B 瘦 tarball）：
#   1. 拉 xiaobei-{tag}-win-x64.tar.gz（atomgit CDN，Windows bsdtar 原生支持 gzip，免装 zstd）
#   2. 解压到 $XIAOBEI_HOME（默认 $env:USERPROFILE\xiaobei，程序目录）
#   3. portable node + pnpm install --prod --frozen-lockfile（在 openclaw\ 下）
#   4. pip install --user（skills 的 python deps，有 python 才跑）
#   5. 放 config-templates\openclaw.json → $OPENCLAW_HOME\openclaw.json + 预填微信 binding
#   6. setup-crew.sh（需 bash：Git Bash 或 WSL；无则警告并跳过，用户后续手动跑）
#   7. camoufox-cli：.cmd shim + camoufox-cli install 下 Firefox
#   8. openclaw-weixin 插件：openclaw plugins install ... --pin（npmmirror）
#   9. 交互问 AWK_API_KEY → 写 daemon.env + setx 用户环境变量 → 尝试 openclaw daemon install
#
# 目录职责：$XIAOBEI_HOME（~\xiaobei）= 程序；$OPENCLAW_HOME（~\.openclaw）= 运行数据。
# Windows 原生 wrapper：$XIAOBEI_HOME\bin\openclaw.cmd（WSL/Git Bash 用户也可用 bin\openclaw）。

$ErrorActionPreference = "Stop"

# ─── 常量 / 目录 ───────────────────────────────────────────────
# atomgit 专线常量（host/版本与 GitHub 不同，不依赖运行时开关）：
#   tarball 直链 host = atomgit.com（redirect 到 file-cdn.gitcode.com 签名 CDN，匿名 GET 可下，~140MB）
#   解 latest tag 走 api.atomgit.com/api/v5（NOT Gitea v1，host/版本都不同）
$Repo = "wiseflow/xiaobei"
$AtomgitMirror = "https://atomgit.com/wiseflow/xiaobei"
$AtomgitApi = "https://api.atomgit.com/api/v5/repos/wiseflow/xiaobei"

$Root = if ($env:XIAOBEI_HOME) { $env:XIAOBEI_HOME } else { Join-Path $env:USERPROFILE "xiaobei" }
$OpenclawHome = if ($env:OPENCLAW_HOME) { $env:OPENCLAW_HOME } else { Join-Path $env:USERPROFILE ".openclaw" }

# 行为开关（环境变量，=1 启用）
$Force        = ($env:XIAOBEI_FORCE         -eq "1" -or $env:XIAOBEI_FORCE         -eq "true")
$SkipBind     = ($env:XIAOBEI_SKIP_BIND    -eq "1" -or $env:XIAOBEI_SKIP_BIND    -eq "true")
$SkipBrowser  = ($env:XIAOBEI_SKIP_BROWSER -eq "1" -or $env:XIAOBEI_SKIP_BROWSER -eq "true")
$NoPrompt     = ($env:XIAOBEI_NO_PROMPT   -eq "1" -or $env:XIAOBEI_NO_PROMPT   -eq "true")

$NodeExe   = Join-Path $Root "tools\node\node.exe"
$NpmCmd    = Join-Path $Root "tools\node\npm.cmd"
$PnpmMjs   = Join-Path $Root "tools\pnpm\bin\pnpm.mjs"
$ClawCmd   = Join-Path $Root "bin\openclaw.cmd"
$ClawSh    = Join-Path $Root "bin\openclaw"

function Write-Stage([string]$msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok([string]$msg)    { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn([string]$msg)  { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)   { Write-Host "  [X]  $msg" -ForegroundColor Red }

# 跑原生命令并按行回显 stdout+stderr。pip/npm/camoufox-cli/openclaw 正常会把进度和警告写 stderr，
# 而本脚本顶部 $ErrorActionPreference="Stop" 会把 2>&1 合并进管道的 stderr 行当 terminating error
# 抛 NativeCommandError/RemoteException（用户 Win 实测卡在 pip install 这步）。这里临时切到 Continue
# 跑原生命令，$LASTEXITCODE 仍由调用方据以判成败。
function Invoke-Streamed([scriptblock]$sb) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $sb 2>&1 | ForEach-Object { Write-Host "    $_" } }
    finally { $ErrorActionPreference = $prev }
}

# 同 Invoke-Streamed，但把 stdout+stderr 合并成字符串返回（供调用方 -&match）。`2>$null` 在
# Windows PowerShell 5.1 + Stop 下压不住 .cmd 的 stderr 仍抛 NativeCommandError，这里用 Continue + 2>&1 纳。
function Capture-Streamed([scriptblock]$sb) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { return (& $sb 2>&1 | Out-String) }
    finally { $ErrorActionPreference = $prev }
}

# ─── 1. 解析最新 release tag（atomgit v5 API）────────────────────
function Resolve-Tag {
    if ($env:XIAOBEI_TAG) { return $env:XIAOBEI_TAG }
    try {
        $rel = Invoke-RestMethod "$AtomgitApi/releases/latest" -Headers @{ "User-Agent" = "xiaobei-install" }
        if ($rel.tag_name) { return $rel.tag_name }
    } catch { Write-Warn "atomgit v5 API 拉取失败，请手动设 `$env:XIAOBEI_TAG=` 后重跑" }
    throw "无法解析最新 release tag（atomgit v5 API）"
}

# ─── 2. 下载 tarball（atomgit CDN）──────────────────────────────
function Download-Tarball([string]$tag) {
    $asset = "xiaobei-$tag-win-x64.tar.gz"
    if ($env:XIAOBEI_TARBALL -and (Test-Path $env:XIAOBEI_TARBALL)) {
        Write-Ok "用本地 tarball：$env:XIAOBEI_TARBALL"
        return $env:XIAOBEI_TARBALL
    }
    $tmp = New-TemporaryFile
    $url = "$AtomgitMirror/releases/download/$tag/$asset"
    Write-Host "  下载 $url"
    Invoke-WebRequest -Uri $url -OutFile $tmp -Headers @{ "User-Agent" = "xiaobei-install" }
    return $tmp.FullName
}

# ─── 3. 解压 ───────────────────────────────────────────────────
function Extract-Tarball([string]$tarball) {
    if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
        throw "未找到 tar（Windows 10 1803+ 自带 bsdtar；请升级 Windows 或装 Git Bash）"
    }
    New-Item -ItemType Directory -Force -Path $Root | Out-Null
    Write-Host "  解压到 $Root"
    & tar -xzf $tarball -C $Root
    if ($LASTEXITCODE -ne 0) { throw "tar 解压失败 (exit $LASTEXITCODE)" }
}

# ─── 4. pnpm install --prod ────────────────────────────────────
function Install-Deps {
    Write-Stage "Installing dependencies (pnpm install --prod)"
    $openclawDir = Join-Path $Root "openclaw"
    if (-not (Test-Path $NodeExe)) { throw "portable node 未找到：$NodeExe" }
    Push-Location $openclawDir
    try {
        # postinstall 子进程（esbuild/protobufjs 等）按 PATH 找 node；目标机器多半没装全局
        # Node（'node' is not recognized 实测），把 portable node 前置进 PATH
        $env:PATH = "$(Split-Path $NodeExe);$env:PATH"
        # pnpm 11 不认 npm_config_registry 环境变量（实测仍走 registry.npmjs.org），用显式 --registry
        $env:npm_config_registry = "https://registry.npmmirror.com"
        & $NodeExe $PnpmMjs install --prod --frozen-lockfile --registry https://registry.npmmirror.com
        if ($LASTEXITCODE -ne 0) { throw "pnpm install 失败 (exit $LASTEXITCODE)" }
        Write-Ok "deps installed"
    } finally { Pop-Location }
}

# ─── 5. python skill deps ──────────────────────────────────────
function Install-PythonDeps {
    Write-Stage "Installing python skill deps"
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { Write-Warn "未找到 python，跳过 skill python deps"; return }
    $reqs = @()
    $reqs += Get-ChildItem -Path (Join-Path $Root "skills") -Filter "requirements.txt" -Recurse -ErrorAction SilentlyContinue
    $reqs += Get-ChildItem -Path (Join-Path $Root "crews") -Filter "requirements.txt" -Recurse -ErrorAction SilentlyContinue
    $reqs += Get-ChildItem -Path $Root -Filter "requirements.txt" -ErrorAction SilentlyContinue
    $reqs = $reqs | Select-Object -ExpandProperty FullName -Unique
    if (-not $reqs) { Write-Ok "无 requirements.txt"; return }
    # 各行作为 pip 命令行参数传入（非 -r 文件），必须剥掉行内注释（pip 只在
    # requirements 文件里认注释，参数里 `Pillow # 说明` 直接 Invalid requirement 报错）；
    # 文件是 UTF-8，显式指定编码防中文注释被 ANSI 误读产生乱码参数。
    $merged = ($reqs | ForEach-Object { Get-Content $_ -Encoding UTF8 -ErrorAction SilentlyContinue } |
        ForEach-Object { ($_ -replace '#.*$', '').Trim() } |
        Where-Object { $_ } | Sort-Object -Unique)
    if (-not $merged) { Write-Ok "无 python 依赖"; return }
    Invoke-Streamed { python -m pip install --user $merged }
    if ($LASTEXITCODE -ne 0) { Write-Warn "pip install 非零退出；可后续手动补装 skills 的 python 依赖" }
    else { Write-Ok "python deps installed" }
}

# ─── 6. 放 config template（对齐 install.sh place_config_template）────
# template 已预置 channels.openclaw-weixin / bindings / session.dmScope，不再运行时 mutate
# （sh 版曾因运行时 mutate 把 plugins 顶层写坏致 "Invalid input"，已同构移除）。
# 健康检查：现有 config 缺 models/agents.defaults（多半是 Install-WeixinPlugin 先跑时
# openclaw plugins install 自建的极简 config，或 openclaw 首启自动生成）→ 备份后用
# template 覆盖，否则 channels/bindings 永远缺失、小贝起不来。
function Place-Config {
    Write-Stage "Placing config template"
    New-Item -ItemType Directory -Force -Path $OpenclawHome | Out-Null
    $cfg = Join-Path $OpenclawHome "openclaw.json"
    $tmpl = Join-Path $Root "config-templates\openclaw.json"
    if (-not (Test-Path $tmpl)) { Write-Err "config template 缺失：$tmpl（tarball 损坏?）"; return }

    $needPlace = $false; $reason = ""
    if (-not (Test-Path $cfg)) { $needPlace = $true; $reason = "不存在" }
    elseif ($Force) { $needPlace = $true; $reason = "XIAOBEI_FORCE=1" }
    else {
        try {
            # 必须显式按 UTF-8 读：openclaw 写的 config 是 UTF-8 无 BOM，PS 5.1 的
            # Get-Content 默认按 ANSI 代码页读，中文路径旁的 \\ 转义会被双字节吞掉，
            # 有效 config 被误判"解析失败"遭覆盖（本机实测）。
            $j = [System.IO.File]::ReadAllText($cfg) | ConvertFrom-Json -ErrorAction Stop
            if (-not ($j.models -and $j.agents -and $j.agents.defaults)) { $needPlace = $true; $reason = "缺 models/agents.defaults（疑似被极简化）" }
        } catch { $needPlace = $true; $reason = "解析失败" }
    }
    if ($needPlace) {
        if (Test-Path $cfg) {
            $bak = "$cfg.bak.$([int][double]::Parse((Get-Date -UFormat %s)))"
            Copy-Item $cfg $bak
            Write-Warn "openclaw.json $reason → 用 template 覆盖（旧文件备份到 $bak）"
        }
        Copy-Item $tmpl $cfg -Force
        Write-Ok "placed openclaw.json template"
    } else {
        Write-Ok "openclaw.json 已存在且健康（有 models + agents.defaults），保留"
    }

    # 把 plugins.load.paths 里的 ${XIAOBEI_HOME} env ref 解析成绝对路径，避免 CLI 上下文没
    # XIAOBEI_HOME 时 "plugin path not found" 误报；AWK_API_KEY 是 secret 保持 env ref 不动。
    # 文本级替换（template 中 ${XIAOBEI_HOME} 仅出现在 plugins.load.paths）；JSON 字符串里
    # 反斜杠是转义符，路径统一写正斜杠。幂等：已解析则 no-op。
    $raw = [System.IO.File]::ReadAllText($cfg)
    if ($raw.Contains('${XIAOBEI_HOME}')) {
        $rootFwd = $Root -replace '\\', '/'
        [System.IO.File]::WriteAllText($cfg, $raw.Replace('${XIAOBEI_HOME}', $rootFwd), [System.Text.UTF8Encoding]::new($false))
        Write-Ok "resolved XIAOBEI_HOME refs -> $rootFwd"
    }
}

# ─── 7. setup-crew（需 bash）──────────────────────────────────
# 找一个真正可用的 bash：优先 Git Bash（吃得了 C:/ 魔格路径）；PATH 里的 bash 可能是
# C:\Windows\system32\bash.exe（WSL 启动器）——没装发行版时直接报错退出，且 WSL bash
# 对 Windows 路径参数不做转换，都不能直接用。每个候选实测 `bash -c echo` 通过才算数。
function Find-WorkingBash {
    $candidates = @()
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        $gitRoot = Split-Path (Split-Path $git.Source)
        $candidates += (Join-Path $gitRoot "bin\bash.exe")
        $candidates += (Join-Path $gitRoot "usr\bin\bash.exe")
    }
    $candidates += "$env:ProgramFiles\Git\bin\bash.exe"
    $candidates += "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
    $inPath = Get-Command bash -ErrorAction SilentlyContinue
    # system32 的 WSL 启动器排最后（仅当其可用且无 Git Bash 时兜底）
    if ($inPath) { $candidates += $inPath.Source }
    foreach ($b in $candidates) {
        if ($b -and (Test-Path $b)) {
            $out = Capture-Streamed { & $b -c "echo __bash_ok__" }
            if ($out -match "__bash_ok__") { return $b }
        }
    }
    return $null
}

function Run-SetupCrew {
    Write-Stage "Setting up crew templates (needs bash)"
    $sh = Join-Path $Root "scripts\setup-crew.sh"
    if (-not (Test-Path $sh)) { Write-Warn "setup-crew.sh 不在 tarball 内，跳过"; return }
    $bashExe = Find-WorkingBash
    if (-not $bashExe) {
        Write-Warn "未找到可用的 bash（setup-crew.sh 是 bash 暑本；注意 system32\bash.exe 是 WSL 启动器，没装发行版不可用）"
        Write-Host "    请装 Git Bash（https://git-scm.com）或 WSL 发行版，然后手动跑："
        Write-Host "      set OPENCLAW_HOME=$OpenclawHome"
        Write-Host "      set XIAOBEI_BIN_DIR=$(Join-Path $Root 'bin')"
        Write-Host "      bash `"$sh`""
        return
    }
    Write-Host "  bash: $bashExe"
    # bash 不认反斜杠（会被当转义），传正斜杠路径给 setup-crew.sh
    # ⚠️ 用 OPENCLAW_STATE_DIR 而非 OPENCLAW_HOME：引擎 resolveStateDir 把 OPENCLAW_HOME 当 homedir
    # 再 append /.openclaw（见 openclaw/src/config/paths.ts），若设 OPENCLAW_HOME=~/.openclaw 会产出
    # ~/.openclaw/.openclaw 嵌套层——后续 weixin/gateway CLI 调用都把 config/npm/openclaw.sqlite 写嵌套层，
    # 外层正解路径反而空（本机实测真 bug）。OPENCLAW_STATE_DIR 引擎当直接 state dir、不 append。
    $env:OPENCLAW_STATE_DIR = ($OpenclawHome -replace '\\', '/')
    $env:XIAOBEI_BIN_DIR = ((Join-Path $Root "bin") -replace '\\', '/')
    Invoke-Streamed { & $bashExe ($sh -replace '\\', '/') }
    if ($LASTEXITCODE -ne 0) { Write-Warn "setup-crew.sh 非零退出（可后续手动 --force 修复）" }
    else { Write-Ok "crew templates set up" }
}

# ─── 8. camoufox-cli ───────────────────────────────────────────
function Install-CamoufoxCli {
    if ($SkipBrowser) {
        Write-Host "  [i]  跳过 camoufox-cli 浏览器二进制（XIAOBEI_SKIP_BROWSER=1）；后续手动：camoufox-cli install" -ForegroundColor Yellow
        return
    }
    Write-Stage "Installing camoufox-cli browser"
    $fork = Join-Path $Root "camoufox-cli"
    if (-not (Test-Path $fork)) { Write-Warn "camoufox-cli fork 不在 tarball 内：$fork；跳过"; return }
    # $Root\bin 放 camoufox-cli.cmd shim，前置进 PATH 让下面 `camoufox-cli install` 找得到
    $env:PATH = "$(Join-Path $Root 'bin');$(Split-Path $NodeExe);$env:PATH"
    $env:npm_config_registry = "https://registry.npmmirror.com"
    $camoufoxBin = Join-Path $Root "bin\camoufox-cli.cmd"
    $cliJs = Join-Path $fork "dist\cli.js"
    $hasDeps = Test-Path (Join-Path $fork "node_modules\camoufox-js")

    # fork 运行时依赖：dist 是 tsc 编译，camoufox-js/playwright-core/pdf-lib 是 external import，
    # 运行时靠 fork 目录下的 node_modules 解析。tarball 为瘦身 ship 的 fork 不带 node_modules。
    if (-not $hasDeps) {
        Push-Location $fork
        try {
            & $NpmCmd install --omit=dev
            if ($LASTEXITCODE -ne 0) { Write-Warn "camoufox-cli fork deps install 失败"; return }
        } finally { Pop-Location }
    }

    # Windows 不走 `npm install -g $fork`：npm 把 fork 装进 $prefix\node_modules 时撞 fork 源目录
    # 本身（EEXIST: file already exists $Root\camoufox-cli）——Windows npm 不能像 Linux 那样 symlink
    # 到源目录。改仿 openclaw.cmd 写 .cmd shim 直接跑 node $fork\dist\cli.js，fork 的 node_modules
    # 已就位，Node 从 cli.js 向上解析依赖；camoufox-cli JS 用 __dirname 定位自身包根，行为与全局装一致。
    if (-not (Test-Path $cliJs)) { Write-Warn "camoufox-cli 入口未找到：$cliJs；跳过"; return }
    $shimLines = @(
        '@echo off'
        'setlocal'
        'set "HERE=%~dp0.."'
        '"%HERE%\tools\node\node.exe" "%HERE%\camoufox-cli\dist\cli.js" %*'
    )
    Set-Content -Path $camoufoxBin -Value $shimLines -Encoding ASCII
    Write-Ok "camoufox-cli shim written: $camoufoxBin"

    Write-Host "  下 Firefox binary（首次 ~557MB）..."
    Invoke-Streamed { camoufox-cli install }
    if ($LASTEXITCODE -ne 0) { Write-Warn "camoufox-cli install 失败；可后续手动：camoufox-cli install" }
    else { Write-Ok "camoufox-cli ready" }
}

# ─── 9. openclaw-weixin 插件 ──────────────────────────────────
function Install-WeixinPlugin {
    Write-Stage "Installing WeChat plugin"
    if (-not (Test-Path $ClawCmd)) { Write-Warn "openclaw wrapper 未找到：$ClawCmd；跳过"; return }
    $pkg = "@tencent-weixin/openclaw-weixin"; $ver = "2.4.6"
    $pin = Join-Path $Root "openclaw-weixin.version.json"
    if (Test-Path $pin) {
        try {
            $j = Get-Content $pin -Raw | ConvertFrom-Json
            $pkg = $j.'openclaw-weixin'.package; $ver = $j.'openclaw-weixin'.version
        } catch { Write-Warn "pin 文件解析失败，用默认 $pkg@$ver" }
    }
    $env:npm_config_registry = "https://registry.npmmirror.com"
    $listOut = Capture-Streamed { & $ClawCmd plugins list }
    if ($listOut -match "openclaw-weixin") { Write-Ok "openclaw-weixin plugin already installed"; return }
    Invoke-Streamed { & $ClawCmd plugins install "$pkg@$ver" --pin }
    if ($LASTEXITCODE -eq 0) { Write-Ok "openclaw-weixin plugin installed" }
    else { Write-Warn "插件安装失败；可后续手动：$ClawCmd plugins install $pkg@$ver --pin" }
}

# ─── 10. awada 本地插件 deps（ws + zod）──────────────────────
function Install-AwadaPlugin {
    Write-Stage "Installing awada plugin deps"
    $awada = Join-Path $Root "awada"
    if (-not (Test-Path $awada)) { Write-Warn "awada 不在 tarball 内：$awada；跳过"; return }
    $hasWs   = Test-Path (Join-Path $awada "node_modules\ws")
    $hasZod  = Test-Path (Join-Path $awada "node_modules\zod")
    if ($hasWs -and $hasZod) { Write-Ok "awada deps already installed"; return }
    $env:npm_config_registry = "https://registry.npmmirror.com"
    Push-Location $awada
    try {
        & $NpmCmd install --omit=dev
        if ($LASTEXITCODE -eq 0) { Write-Ok "awada deps installed" }
        else { Write-Warn "awada deps install 失败；可后续手动：cd $awada ; npm install --omit=dev" }
    } finally { Pop-Location }
}

# ─── 10.5 修复 daemon 启动脚本编码（openclaw 上游 bug 的 workaround）──
# openclaw daemon install 写出的 gateway.cmd / gateway.vbs 是 UTF-8（无 BOM），
# 而 cmd.exe / WScript 按系统 ANSI 代码页读取脚本文件——安装路径含非 ASCII 字符
# （如中文用户名）时路径变乱码，node.exe 找不到，gateway 永远起不来（本机实测）。
# workaround：把长路径替换成 8.3 矫路径（纯 ASCII）后以 ASCII 重写；无 8.3 名
# 可用时退回按 ANSI 代码页写（cmd.exe 按 ANSI 读，编码一致即可）。幂等。
function Repair-GatewayCmd {
    $files = @((Join-Path $OpenclawHome "gateway.cmd"), (Join-Path $OpenclawHome "gateway.vbs"))
    $fso = $null
    foreach ($f in $files) {
        if (-not (Test-Path $f)) { continue }
        $txt = [System.IO.File]::ReadAllText($f, [System.Text.UTF8Encoding]::new($false))
        if ($txt -notmatch '[^\x00-\x7F]') { continue }
        if (-not $fso) { $fso = New-Object -ComObject Scripting.FileSystemObject }
        $dirs = @($Root, $OpenclawHome, $env:USERPROFILE) | Sort-Object Length -Descending
        foreach ($d in $dirs) {
            try { $short = $fso.GetFolder($d).ShortPath } catch { continue }
            if ($short -and $short -ne $d) { $txt = $txt.Replace($d, $short) }
        }
        if ($txt -match '[^\x00-\x7F]') {
            [System.IO.File]::WriteAllText($f, $txt, [System.Text.Encoding]::Default)
        } else {
            [System.IO.File]::WriteAllText($f, $txt, [System.Text.ASCIIEncoding]::new())
        }
        Write-Ok "修复 $(Split-Path $f -Leaf) 编码（非 ASCII 路径 → 8.3 矫路径）"
    }
}

# ─── 11. 交互收 AWK_API_KEY + 起 gateway ──────────────────────
# env 分工（对齐 install.sh / 上游踩坑经验）：
#   ~/.openclaw/.env        ← 业务变量（AWK_API_KEY/XIAOBEI_HOME/OPENCLAW_STATE_DIR），openclaw CLI 裸跑用
#   ~/.openclaw/daemon.env  ← gateway service 用，只放 3 个固定值（OPENCLAW_BROWSER_TIMEOUT_MS/
#                              OPENCLAW_DISABLE_BONJOUR/PATH）+ OPENCLAW_STATE_DIR
# 原因：Linux systemd 那套 EnvironmentFile= 加载器对含特殊字符的业务变量（PATH 带分号、
# AWK_API_KEY 带连字符）有踩坑历史，业务变量挪 .env 让 systemd 只加载稳的固定值。
# Windows 不走 systemd，gateway.cmd 的 `call daemon.env` 没这个坑，但为风格统一照此分工。
function Install-GatewayAndEnv {
    Write-Stage "Configuring API key and gateway"
    New-Item -ItemType Directory -Force -Path $OpenclawHome | Out-Null
    $dotEnv    = Join-Path $OpenclawHome ".env"
    $daemonEnv = Join-Path $OpenclawHome "daemon.env"

    # ─── 检测/清掉错误的 OPENCLAW_HOME 用户环境变量 ───────────────
    # 引擎 resolveStateDir 把 OPENCLAW_HOME 当 homedir 再 append /.openclaw（见
    # openclaw/src/config/paths.ts），故若 OPENCLAW_HOME 已被设成 ~/.openclaw，会产出
    # ~/.openclaw/.openclaw 嵌套路径——openclaw.json、daemon.env、lastTouch 全落嵌套层，
    # 外层正解路径反而空（本机实测过的真 bug）。state dir 应该用 OPENCLAW_STATE_DIR 显式
    # 覆盖（引擎把它当直接 state dir、不 append），OPENCLAW_HOME 不该在用户环境里设。
    $badHome = $env:OPENCLAW_HOME
    if ($badHome -and ($badHome.TrimEnd('\').ToLower() -eq $OpenclawHome.TrimEnd('\').ToLower())) {
        Write-Warn "检测到 OPENCLAW_HOME=$badHome 已设成 state dir 路径"
        Write-Warn "  这会让引擎嵌套 append /.openclaw → ~/.openclaw/.openclaw/，config 全落错位置"
        Write-Warn "  正解：清掉 OPENCLAW_HOME，改用 OPENCLAW_STATE_DIR 显式指定 state dir"
        try {
            [Environment]::SetEnvironmentVariable("OPENCLAW_HOME", $null, "User")
            [Environment]::SetEnvironmentVariable("OPENCLAW_HOME", $null, "Process")
            Remove-Item Env:OPENCLAW_HOME -ErrorAction SilentlyContinue
            Write-Ok "已从用户环境变量清掉 OPENCLAW_HOME（新终端生效)"
        } catch { Write-Warn "清 OPENCLAW_HOME 失败，请手动删：[Environment]::SetEnvironmentVariable('OPENCLAW_HOME', `$null, 'User')" }
    }

    # ─── 交互收 AWK_API_KEY ───────────────────────────────────
    $awkKey = $env:AWK_API_KEY
    if (-not $NoPrompt -and -not $awkKey) {
        $awkKey = Read-Host "Enter AWK_API_KEY (Volces ARK API key)"
    }

    # ─── 写 .env（业务变量，export 格式给 bash/sh source 用，CLI 裸跑读这个）────
    # 幂等：先剥同 key 旧行再追加。AWK_API_KEY 是 secret，单引号裹 + '\'' 转义内置单引号。
    $exportLines = @()
    if (Test-Path $dotEnv) { $exportLines = Get-Content $dotEnv }
    $exportLines = $exportLines | Where-Object { $_ -notmatch "^export AWK_API_KEY=" -and $_ -notmatch "^export XIAOBEI_HOME=" -and $_ -notmatch "^export OPENCLAW_STATE_DIR=" }
    if ($awkKey) {
        $awkEsc = $awkKey -replace "'", "'\''"
        $exportLines += "export AWK_API_KEY='$awkEsc'"
    }
    $rootEsc = $Root -replace "'", "'\''"
    $exportLines += "export XIAOBEI_HOME='$rootEsc'"
    $homeEsc = $OpenclawHome -replace "'", "'\''"
    $exportLines += "export OPENCLAW_STATE_DIR='$homeEsc'"
    Set-Content -Path $dotEnv -Value $exportLines -Encoding UTF8
    Write-Ok ".env written (业务变量，CLI 裸跑用)"

    # ─── 写 daemon.env（gateway service 用，KEY=value 格式给 gateway.cmd call 用）──
    # 只放 3 个固定值 + OPENCLAW_STATE_DIR（gateway 子进程需要 state dir 消歧嵌套）。
    $daemonLines = @()
    if (Test-Path $daemonEnv) { $daemonLines = Get-Content $daemonEnv }
    $daemonLines = $daemonLines | Where-Object { $_ -notmatch "^OPENCLAW_BROWSER_TIMEOUT_MS=" -and $_ -notmatch "^OPENCLAW_DISABLE_BONJOUR=" -and $_ -notmatch "^PATH=" -and $_ -notmatch "^OPENCLAW_STATE_DIR=" }
    $daemonLines += "OPENCLAW_BROWSER_TIMEOUT_MS=90000"
    $daemonLines += "OPENCLAW_DISABLE_BONJOUR=true"
    $daemonLines += "OPENCLAW_STATE_DIR=$OpenclawHome"
    $pathLine = "PATH=$(Join-Path $Root 'bin');$(Split-Path $NodeExe);$env:PATH"
    $daemonLines += $pathLine
    Set-Content -Path $daemonEnv -Value $daemonLines -Encoding UTF8
    Write-Ok "daemon.env written (gateway service 用，3 固定值 + PATH + OPENCLAW_STATE_DIR)"

    # 把 .env 业务变量加载进当前 install shell，让后续 daemon install / gateway restart / channels login
    # 校验 config 时能解析到 AWK_API_KEY / XIAOBEI_HOME（CLI 裸跑本会 . .env，install shell 也得有）
    if ($awkKey) { $env:AWK_API_KEY = $awkKey }
    $env:XIAOBEI_HOME = $Root
    $env:OPENCLAW_STATE_DIR = $OpenclawHome

    # setx 用户环境变量（让新终端 / gateway 子进程继承 AWK_API_KEY）
    if ($awkKey) {
        & setx AWK_API_KEY "$awkKey" | Out-Null
        Write-Ok "AWK_API_KEY set as user env var (新终端生效)"
    }

    # 尝试 daemon install（Windows 支持情况视 openclaw 版本而定）
    Write-Host "  尝试 openclaw daemon install..."
    Invoke-Streamed { & $ClawCmd daemon install }
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "gateway daemon installed"
        Repair-GatewayCmd
        Invoke-Streamed { & $ClawCmd gateway restart }
    } else {
        Write-Warn "openclaw daemon install 在 Windows 未就绪或失败"
        Write-Host "  请开新 PowerShell 终端前台跑 gateway："
        Write-Host "    set AWK_API_KEY=$awkKey"
        Write-Host "    $ClawCmd gateway start"
    }
}

# ─── 12. 自动出微信绑定二维码（首装末尾）──────────────────────
function Test-WeixinBound {
    $paths = @(
        (Join-Path $OpenclawHome "openclaw-weixin\accounts.json"),
        (Join-Path $OpenclawHome ".openclaw\openclaw-weixin\accounts.json")
    )
    foreach ($p in $paths) { if (Test-Path $p) { return $true } }
    return $false
}

function Bind-WeixinChannel {
    if ($SkipBind -or $NoPrompt) {
        Write-Host "  [i]  跳过微信扫码绑定（XIAOBEI_SKIP_BIND / XIAOBEI_NO_PROMPT=1）；后续手动跑：openclaw channels login --channel openclaw-weixin" -ForegroundColor Yellow
        return
    }
    if (Test-WeixinBound) { Write-Ok "检测到微信账号已绑定，跳过扫码"; return }
    if (-not (Test-Path $ClawCmd)) { Write-Warn "openclaw wrapper 未找到（$ClawCmd），跳过微信绑定"; return }
    Write-Stage "绑定微信 channel（用手机扫码）"
    Write-Host "  接下来会出二维码，用微信扫一下、点确认，小贝就能用了。"
    Write-Host "  扫码慢没关系，二维码会自动刷新；扫完即继续。"
    Write-Host ""
    for ($i = 1; $i -le 5; $i++) {
        & $ClawCmd channels login --channel openclaw-weixin
        if (Test-WeixinBound) { Write-Ok "微信账号绑定成功"; return }
        if ($i -lt 5) { Write-Warn "本轮未检测到绑定，重出二维码（第 $($i + 1) 次）..." }
    }
    Write-Warn "多次扫码未完成绑定。可后续手动跑：$ClawCmd channels login --channel openclaw-weixin"
}

# ─── main ─────────────────────────────────────────────────────
function Main {
    Write-Host "wiseflow installer (Windows, atomgit) — 预构建 tarball 路线" -ForegroundColor Magenta
    Write-Host "  Program dir : $Root"
    Write-Host "  Runtime dir : $OpenclawHome"
    Write-Host "  Repo        : $Repo (atomgit)"

    # 检测是否已装（决定走 update 还是 fresh install）
    $cfgExisting = Join-Path $OpenclawHome "openclaw.json"
    $isUpdate = (Test-Path $cfgExisting) -and -not $Force
    if ($isUpdate) {
        Write-Warn "检测到已有安装（$cfgExisting）→ 走更新路线，保留运行数据（XIAOBEI_FORCE=1 可强覆盖）"
        # 先停 gateway（对齐 install.sh stop_gateway_if_running）：否则 tar 覆盖
        # tools\node\node.exe、pnpm 重写 node_modules 会撞运行中 gateway 的文件锁
        # （"Can't unlink already-existing object: Permission denied"，本机实测）
        Write-Stage "Stopping gateway before update"
        if (Test-Path $ClawCmd) { Invoke-Streamed { & $ClawCmd gateway stop } }
        Get-Process node -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -like "$Root*" } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }

    Write-Stage "Resolving latest release (atomgit v5 API)"
    $tag = Resolve-Tag
    Write-Ok "tag = $tag"

    Write-Stage "Downloading pre-built tarball (atomgit CDN)"
    $tb = Download-Tarball $tag

    Write-Stage "Extracting tarball"
    Extract-Tarball $tb

    Install-Deps
    Install-PythonDeps
    Install-AwadaPlugin
    Install-CamoufoxCli
    Install-WeixinPlugin

    if ($isUpdate) {
        # 更新路线也自愈 config（对齐 install.sh：openclaw.json 若被极简化则用 template 修复）
        Place-Config
        Write-Stage "Refreshing gateway env and restarting"
        $envFile = Join-Path $OpenclawHome "daemon.env"
        if (Test-Path $envFile) {
            $lines = Get-Content $envFile
            $lines = $lines | Where-Object { $_ -notmatch "^XIAOBEI_HOME=" }
            $lines += "XIAOBEI_HOME=$Root"
            Set-Content -Path $envFile -Value $lines -Encoding UTF8
            Write-Ok "daemon.env XIAOBEI_HOME refreshed"
        }
        Repair-GatewayCmd
        Invoke-Streamed { & $ClawCmd gateway restart }
    } else {
        Place-Config
        Run-SetupCrew
        Install-GatewayAndEnv
        Bind-WeixinChannel
    }

    Write-Host ""
    if ($isUpdate) {
        Write-Host "wiseflow updated successfully!" -ForegroundColor Green
    } else {
        Write-Host "wiseflow installed successfully!" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    $binDir = Join-Path $Root 'bin'
    Write-Host "  把 $binDir 加到用户 PATH（安全方式，勿用 setx %PATH% 会截断）："
    Write-Host "    [Environment]::SetEnvironmentVariable('PATH', `"$binDir;`" + [Environment]::GetEnvironmentVariable('PATH','User'), 'User')"
    Write-Host ""
    Write-Host "  Dashboard: http://127.0.0.1:18789"
    Write-Host "  Update later: re-run this install script (preserves $OpenclawHome runtime data)."
    Write-Host ""
}

Main
