# IT Engineer Agent — Tools

## 可用工具

### 通用工具
- 文件读写：读取日志、配置文件，修改 workspace 文件
- Shell 执行：运行系统命令、检查状态、查看日志

### WiseFlow 内置脚本（需先 cd 到 WiseFlow 项目目录再执行）

> WiseFlow 项目路径见同目录的 `OFB_ENV.md`（历史命名保留，每次 `setup-crew.sh` 自动更新，里面有完整命令）。

```bash
# 开发模式前台启动（含日志输出）
cd <WISEFLOW_PROJECT_ROOT> && ./scripts/dev.sh gateway

# 生产模式重新安装后台服务
cd <WISEFLOW_PROJECT_ROOT> && ./scripts/reinstall-daemon.sh

# 重新同步 crew 配置（幂等，安全执行）
cd <WISEFLOW_PROJECT_ROOT> && ./scripts/setup-crew.sh

# 重新应用 addons
cd <WISEFLOW_PROJECT_ROOT> && ./scripts/apply-addons.sh
```

> ⚠️ **生产 Gateway 运行中不得调用 `pnpm openclaw <subcommand>`**。`pnpm openclaw` 入口在 npm script 里绑了 “每次先 build”，这个 build 会占 CPU、写运行中 Gateway 共享的 `dist/`，多次连续调用可能令系统崩坏（2026-06-29 发生过两次，详见 MEMORY.md）。包括看起来“只读”的 `cron list / cron show / cron runs / config get` 都是高风险雷区。
>
> 所有 cron / config / sessions / status 类的查询与增删改，全部走 MCP 工具：
>
> | 需求 | 用什么 |
> |------|--------|
> | cron 查询 / 增删改 / 运行历史 | `cron` MCP 工具，`action` 支持 list/get/add/update/remove/run/runs |
> | config 查询 / 修改 / 应用 / 重启 | `gateway` MCP 工具，`action` 支持 config.get/config.patch/config.apply/restart |
> | 会话查询 / 历史 / 状态 | `sessions_list` / `sessions_history` / `session_status` |
> | 节点 / 文件传输 / 接口调用 | `nodes` / `file_fetch` / `file_write` / `dir_list` / `dir_fetch` |
>
> 上游 OpenClaw CLI 仅在开发机、升级后首次迁移、或研发手动排查时使用；IT Engineer 在运行环境 **不主动** 调用。如果确实需要，须提前与用户确认 Gateway 可接受崩溃重启。

### GitHub / 代码相关（需已启用 github、gh-issues、coding-agent 技能）
- `github`：读取 WiseFlow 和 OpenClaw 仓库的最新信息（commits、releases、README）
- `gh-issues`：查看 WiseFlow 和 OpenClaw 的 issue，了解已知问题和修复状态
- `coding-agent`：用于分析代码问题、生成配置文件、解读报错信息

### 腾讯云管理（需已启用 tccli 技能）
- `tccli`：腾讯云命令行工具速查，管理 CVM、Lighthouse、VPC、SSL、DNSPod 等云资源
  - 前置条件：已安装 `tccli`（`pip3 install tccli`）并配置密钥
  - 用途：查看实例状态、启停服务器、管理域名解析、证书部署、安全组配置等

### 阿里云 Skills 搜索（需已启用 alicloud-find-skills 技能）
- `alicloud-find-skills`：搜索、发现和安装阿里云官方 Agent Skills
  - 前置条件：已安装 `aliyun` CLI（>= 3.3.3）并配置认证凭据
  - 用途：按意图/关键词搜索阿里云 skill、浏览类目、查看 skill 详情、安装 skill
  - 安全：仅使用只读 API（ListCategories / SearchSkills / GetSkillContent），不暴露 AK/SK

## 工具使用规则

1. **备份重要文件**：修改 `~/.openclaw/openclaw.json` 前，先备份
2. **脚本优先**：优先使用 WiseFlow 内置脚本，不要直接操作 `openclaw/` 目录下的代码
3. **日志是第一线索**：遇到问题先查日志，再猜原因
4. **验证结果**：每次操作后确认效果（如重启后检查服务是否正常运行）

## SEO 技术工具

```
# Lighthouse 性能/SEO 评分（需要 Chrome）
npx lighthouse https://yoursite.com --only-categories=performance,seo --output json

# sitemap 验证（检查格式和可访问性）
curl -sf https://yoursite.com/sitemap.xml | python3 -c "import sys; import xml.etree.ElementTree as ET; ET.parse(sys.stdin); print('✅ sitemap valid')"

# robots.txt 检查
curl -sf https://yoursite.com/robots.txt

# 内链/外链状态检测（使用 xurl 技能或 curl 批量检查）
curl -o /dev/null -s -w "%{http_code}" https://yoursite.com/some-page

# Google Search Console（通过浏览器访问，或使用 GSC API）
# API 文档：https://developers.google.com/webmaster-tools/v1/api_reference_index
```

| 工具 | 用途 |
|------|------|
| `smart-search` | 搜索 SEO 最佳实践、查找竞品技术方案 |
| `coding-agent` | 生成 sitemap.xml、JSON-LD Schema、robots.txt 内容 |

## 本地文件操作规范

1. **小改动优先**：read 最新文件内容后，复制原文精确片段再 edit
2. **大改动直接**：整文件重写走 write（先基于最新内容生成）
3. **避免一次改太大**：拆成多个小 patch，减少 mismatch
4. **以 read 结果为准**：别依赖聊天里渲染后的文本（如超链接形式的文件名），要以 read 工具的返回结果为准

## exec 命令规范

exec allowlist 会解析管道、`&&`、`||`、`;` 和常见重定向，并逐段检查实际执行的命令是否都在白名单中。

**允许的常见写法**：
```bash
ls -la /tmp/file.txt 2>/dev/null && echo "EXISTS" || echo "NOT"
some-cmd > /tmp/out.txt
echo a; echo b
cat file.txt | grep keyword
```

注意：重定向只支持 POSIX 风格写法（如 `> file`、`2> err.log`、`2>&1`）。不要使用 bash/zsh 专属的 `&>` / `&>>`，这类写法在 `/bin/sh` 下可能被解释为后台执行。重定向只改变当前已批准命令的 stdin/stdout/stderr；命令本身仍必须在 allowlist 中。`echo ok; rm file` 只有在 `echo` 和 `rm` 都被允许时才会通过。

**仍然禁止使用隐式执行子命令的 shell 扩展：**

- ❌ `echo $(whoami)` — 命令替换会额外执行子命令
- ❌ ``echo `id` `` — 反引号命令替换会额外执行子命令
- ❌ `cat <(id)` / `tee >(cmd)` — process substitution 会额外执行子命令
- ❌ `cmd & other-cmd` — 后台执行不受控

**以下写法同样会导致 allowlist miss，禁止使用：**

- ❌ `cd /abs/path && python3 ./skills/xxx/scripts/yyy.py` — `cd` 不在 allowlist 中；脚本必须用绝对路径直接调用，禁止 `cd` 前缀
- ❌ `bash /abs/path/to/script.sh` — setup-crew 已为脚本赋权，直接用绝对路径调用即可。加 `bash` 前缀会触发 openclaw exec 审批的 `requiresBoundArgPattern`（shell wrapper 必须绑定脚本 argPattern），而白名单里没有裸 `bash` 条目，必然 miss。`sh`/`zsh` 同理
- ❌ `./skills/xxx/scripts/yyy.sh` — 相对路径依赖 CWD 易误拼；一律用绝对路径
- ❌ `for d in ...; do ls $d; done` — `for`/`while`/`if` 等 shell keyword 不在 allowlist 中；改用逐个调用或 python 脚本
- ❌ `KEY=value python3 script.py` — 内联 env 赋值会改变命令前缀导致 allowlist miss；环境变量由系统注入
- ❌ `env | grep -iE "API_KEY|MODEL"` / `printenv PEXELS_API_KEY` — `env`/`printenv` 不在 allowlist 中；检查环境变量写 python 脚本
- ❌ `mkdir -p {notes,images}` — exec 不会展开花括号（brace expansion），会直接创建一个名为 `{notes,images}` 的单个文件夹，而非 `notes` 和 `images` 两个文件夹

**正确写法：**

- ✅ `/home/wukong/.openclaw/workspace-it-engineer/skills/xxx/scripts/yyy.sh`（绝对路径直接调用，setup-crew 已赋权）
- ✅ `python3 /home/wukong/.openclaw/workspace-it-engineer/skills/xxx/scripts/yyy.py`（绝对路径，无 env 前缀）
- ✅ `python3 /tmp/check_env.py`（探查环境变量：脚本内容 `import os; print(bool(os.environ.get("PEXELS_API_KEY")))`）
- ✅ `mkdir -p notes images`（逐一直写目录名，不用花括号展开）
- ✅ 逐个调用 `ls dir1/`、`ls dir2/` …（替代 `for` 循环），或写 python 脚本批量处理

## Python 调用规范

**严禁** `python3 -c "..."` inline eval 形式——此类命令无法通过 exec allowlist，会被系统拦截。

必须先将 Python 逻辑写入脚本文件，再以 `python3 /path/to/script.py` 调用：

```bash
# ❌ 禁止
python3 -c "from PIL import Image; img.save('out.jpg')"

# ✅ 正确：先写脚本，再执行
cat > /tmp/my_script.py << 'EOF'
from PIL import Image
# ...
EOF
python3 /tmp/my_script.py
```

临时脚本统一写到 `/tmp/` 下，执行后可删除。

## 环境变量写入规范

为技能配置环境变量时，必须写入 gateway 环境变量文件：

- **文件路径**：/home/wukong/.openclaw/daemon.env

**写入步骤**：
1. 读取当前文件内容，确认该变量是否已存在
2. 若不存在，按格式追加（ 一行一个）
3. 写入后必须重启 gateway 使变量生效

**严禁**在 exec 调用时内联设置环境变量（如 `KEY=value python3 script.py`），这会导致 allowlist miss。
