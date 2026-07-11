# 浏览器栈整体替换 spec（v5.6.0 重磅）

> 2026-07-11 落盘。本 spec 是上一轮对话（session `29626745`）的决策结晶，供新开对话执行。
> 执行顺序：**先做 §待调研项（openclaw/extensions/browser 替换接口/兼容层调研）**，确认可行后再按 §落地顺序施工。
> 相关 spike 证据见 [`camoufox-spike-2026-07.md`](./camoufox-spike-2026-07.md)。

---

## 0. 决策总览

维持 OpenClaw 架构，**整体替换其浏览器能力**：用改造后的 camoufox-cli（fork，vendor 进代码仓）替换 `openclaw/extensions/browser` extension。全线放弃 patchright patch，browser-guide 技能并入 `/extensions/browser/skill`。

### 核心原则（用户拍板的 8 点 + 补充）

| # | 原则 |
|---|------|
| 0 | **全线使用 forked camoufox-cli**，放弃 patchright 的 patch |
| 1 | 涉及登录的自媒体平台，**每平台一个且只一个持久化 session**，必须顺次使用（fail-first 队列，见 §fork 改造清单） |
| 2 | browser-guide 约定：需要用户配合过验证码的，**必须用 camoufox-cli 有头模式** |
| 3 | login-manager 约定：wechat-channel / wx-mp 登录可无头启动截图发 QR；**douyin / twitter / xhs（xhs-publish \| xhs-browse）/ weibo / zhihu / xianyu 登录必须 有头模式** |
| 4 | login-manager 导出 cookie **同时导出 UA**；所有用中央 cookie 的脚本导入 cookie 同时导入 UA |
| 5 | **严禁浏览器方案导入 cookie**（登录失效必须重新登录流程，见 §profile 丢失处理） |
| 6 | 恢复 twitter-interact 脚本操作模式（参考 AiToEarn 上游，见 §twitter-interact） |
| 7 | wx-mp-hunter 改造纳入上述体系，不再保留单独登录流程 |
| 补充 A | 持久化 vs 临时 session：**涉及登录的站点 → 持久化**（指纹稳定 + cookie 留 profile）；**不涉及登录的站点（新闻等）→ 临时性 session**（每次随机指纹，关闭自清） |
| 补充 B | reddit / youtube 等也是自媒体平台，涉及登录走持久化 |
| 补充 C | patchright 整体去掉（overrides.sh 不再注入 patchright-core） |
| 补充 D | profile 丢失：**重建 + 重登录，绝对不允许导入** |

### 涉及的持久化平台（每平台一个 session）

`douyin` · `twitter` · `xhs`（浏览器操作一套，cookie 分两套见 §login-manager）· `weibo` · `zhihu` · `xianyu` · `wechat-channel`（视频号）· `wx-mp`（公众号）· `reddit` · `youtube`

> xhs 例外：login-manager 导出 cookie **分两套**（xhs-publish creator 域 / xhs-browse 浏览域），对应不同技能脚本；但**浏览器操作部分一套**（一个持久化 session）。

---

## 1. fork camoufox-cli 改造清单

**vendoring 方式**：直接进代码仓 `patches/camoufox-cli/`（不另起 repo，不 npm 发布）。fork 基线 = `camoufox-cli@0.6.2`（本机当前全局版本）。

### 1.1 必改

| 项 | 说明 |
|----|------|
| **upload 命令** | 上游无 upload 命令（命令集：open/back/forward/reload/url/title/close/snapshot/click/fill/type/select/check/hover/press/text/eval/screenshot/pdf/scroll/wait/tabs/switch/close-tab/sessions/cookies/install）。fork 补 `upload <selector> <filepath>`，走 Playwright `setInputFiles`。发布类技能（douyin-publish / xhs-publish / weibo-publish / zhihu-publish / wechat-channels-publish / youtube-publish）依赖此 |
| **fail-first 队列** | 同 session 并发不是良性失败而是互相踩（`server.js:71` 无锁 + `commands.js:24` 共享 page.goto）。fork 内置 **fail-first 队列**：同 session 已有命令在跑时，新命令直接 fail，**失败返回文本写清原因和指导**（"session <name> 正忙，请等待当前操作完成后再试"）。agent 读到 fail 文本知道发生了什么、该干什么（等待重试）。不自动排队、不自动等待——避免隐藏排队语义 |
| **identity export 命令** | fork 加 `identity export` 命令，导出当前 session 的 UA / 指纹摘要（供脚本侧导入 UA，对应原则 4）。与 `cookies export` 对称使用 |

### 1.2 不改（沿用上游）

- `--persistent` 指纹冻结机制（`camoufox-cli.json` 首次生成后冻结，spike ② 已证）
- `cookies export/import` JSON 格式（= Playwright `add_cookies` 格式，spike ① 已证零转换）
- daemon 模型 / `--session` 隔离 / `--json` 信封 / `--headed`/`--headless`

### 1.3 D18 共享模板模式（持久化 session 落地方式）

spike 文档 L30-33 已设计：
1. 一次性 bootstrap：`camoufox-cli --session _template --persistent open about:blank` → 生成冻结 `camoufox-cli.json` → close。
2. 每个持久化平台 session：`mkdir ~/.camoufox-cli/profiles/<platform>` → `cp ~/.openclaw/logins/_template/camoufox-cli.json` 进去 → `camoufox-cli --session <platform> --persistent ...`。
3. 各平台 session 共享指纹，独立 `cookies.sqlite`/state。

> 临时性 session（新闻等不登录站点）不 cp 模板，走默认临时 profile（每次随机指纹，关闭自清）。

---

## 2. openclaw/extensions/browser 替换（⚠️ 待调研）

**目标**：用 forked camoufox-cli 直接替换 `openclaw/extensions/browser` extension，维持 OpenClaw extension 架构。

当前 `openclaw/extensions/browser/` 结构（已确认存在）：
```
browser-bridge.ts / browser-cdp.ts / browser-config.ts / browser-control-auth.ts
browser-doctor.ts / browser-host-inspection.ts / browser-maintenance.ts
browser-profiles.ts / cli-metadata.ts / index.ts / index.test.ts
openclaw.plugin.json / package.json / plugin-registration.ts / register.runtime.ts
runtime-api.ts / setup-api.ts / skills/browser-automation/ / src/ / ...
```

### 2.1 待调研项（下个对话先做）

1. **extension 接口契约**：`openclaw.plugin.json` + `plugin-registration.ts` + `register.runtime.ts` 暴露给 openclaw core 的接口面是什么？core 侧调用 browser extension 的调用点有哪些（grep `extensions/browser` / `browser tool` 引用）？
2. **tool 名注册**：browser extension 向 agent 注册的 tool 名（`browser` / `browser_do` 等）是什么？system prompt 里 browser 工具摘要从哪生成（原 patch 007 注入点）？替换后 tool 名是否保持兼容，还是借机改名？
3. **CDP/Playwright 依赖耦合**：`browser-cdp.ts` / `browser-bridge.ts` 对 patchright-core / playwright-core 的依赖深度。整体替换为 camoufox-cli（子进程 + Unix socket daemon）后，这些 .ts 是全删还是留薄壳转调 forked cli？
4. **profile / session 管理**：`browser-profiles.ts` 的 profile 目录管理 vs camoufox-cli 的 `~/.camoufox-cli/profiles/<session>`。如何统一（D18 模板模式落在 `~/.openclaw/logins/` 还是 `~/.camoufox-cli/profiles/`）？
5. **browser-doctor / maintenance**：`browser-doctor.ts` / `browser-maintenance.ts` 的健康检查 / 清理职责，forked cli 侧如何对应（daemon 超时 / profile 体积回收——`~/.camoufox-cli/profiles/` 已 1.8GB / 22 dir，persistent 不自动清理）？
6. **setup-api.ts**：extension 安装期动作（`camoufox-cli install --with-deps` 等）如何接入？
7. **test-fetch.ts / test-support.ts / index.test.ts**：测试面替换范围。

**调研产出**：一份 `docs/browser-extension-replacement-research.md`，含上述 7 项的接口面清单 + 替换方案（全删 vs 薄壳转调）+ 风险点。**调研结论出来前不动 extension 代码。**

### 2.2 browser-guide 技能并入

当前 `skills/browser-guide/`（全局 skill）+ `openclaw/extensions/browser/skills/browser-automation/`（extension 自带 skill）。

替换后：browser-guide 内容并入 `openclaw/extensions/browser/skill/`（单数，应用更紧密）。全局 `skills/browser-guide/` 删除或留空壳重定向。

---

## 3. patch 重组

`patches/` 当前：`002` / `003` / `005` / `006` / `007` + `overrides.sh` + `generate-patch.sh`。

| patch | 处置 | 原因 |
|-------|------|------|
| `002-disable-web-search-env-var.patch` | **留** | 与浏览器无关，web_search 禁用仍需要 |
| `003-act-field-validation.patch` | **删** | 校验的是被替换掉的 browser tool 的 act 字段，目标代码随 extension 整体替换而消失 |
| `005-browser-timeout-env-var.patch` | **删** | 同上，browser tool 超时环境变量，替换后由 forked cli `--timeout` 接管 |
| `006-connectovercdp-no-defaults.patch` | **删** | patchright `connectOverCDP` 专属，patchright 整体去掉（补充 C） |
| `007-browser-prefer-camoufox-cli.patch` | **删** | 在被替换的 browser tool 摘要里注入"优先 camoufox-cli"，替换后整个 tool 就是 camoufox-cli，注入无意义 |

`overrides.sh`：去掉 patchright-core 注入逻辑（`PATCHRIGHT_VERSION` 相关），保留其他依赖覆盖。`patches/README.md` 同步更新表 + 已删除补丁历史表。

---

## 4. login-manager 改造为纯指导文件

**职责边界**：forked camoufox-cli 加了 `identity export` 命令后，cookie/UA 导出由 forked cli 干。**login-manager 不再有脚本**，变成纯 SKILL.md 指导文件（告诉 agent 各平台登录流程：何时有头 / 何时无头截图 QR / 探活规则 / 中央存储路径约定）。

### 4.1 删除

- `crews/main/skills/login-manager/scripts/login_manager.py`
- `crews/main/skills/login-manager/scripts/login-manager.sh`
- `tests/`

### 4.2 SKILL.md 保留并改写的内容

- 各平台登录模式约定（原则 3）：
  - 无头截图 QR：`wechat-channel` / `wx-mp`
  - 有头手动：`douyin` / `twitter` / `xhs-publish` / `xhs-browse` / `weibo` / `zhihu` / `xianyu` / `reddit` / `youtube`
- 探活规则（各平台登录态检测，参考 `wiseflow-pro/wiseflow4-pro/core/wis/nodriver_helper.py` 的规则：xhs=web_session / wb=SUB+SCF / dy=sessionid+sid_tt+uid_tt / bili=SESSDATA / ks=passToken / zhihu=z_c0 / mp=URL token= / twitter=auth_token 等）
- 中央存储路径约定：`~/.openclaw/logins/<platform>.json`（cookie）+ `~/.openclaw/logins/<platform>.ua.json`（UA，新增）
- xhs 两套 cookie 约定：`xhs-publish.json`（creator 域）/ `xhs-browse.json`（浏览域）
- 流程模板：探活失败 → forked cli 有头/无头启动 → 用户扫码/登录 → `cookies export` + `identity export` → 落盘中央存储 → close session

### 4.3 待同步的 4 个 camoufox-cli 适配 bug fix

上一轮发现的 login-manager 4 个适配 bug，方案确认后随改造一起做（低风险）。具体 bug 清单在上一轮对话中，新对话开始时从 transcript 取或重新排查 `login_manager.py` 对 camoufox-cli 的调用点。

---

## 5. 9+ 平台 skill 逐个改造点

每个涉及浏览器的 skill：把对 patchright / browser tool / 旧 login-manager 脚本的调用，改为调 forked camoufox-cli（绝对路径，遵循 CLAUDE.md「crew 专属 skill 脚本调用必须绝对路径」）+ 读中央 cookie/UA 文件。

| skill | 改造点 |
|-------|--------|
| `xhs-content-ops` | 浏览器取数走 forked cli 持久化 session `xhs`；脚本侧从 `xhs-browse.json` + `.ua.json` 导入 cookie+UA |
| `xhs-publish` | 发布走 forked cli 持久化 session `xhs` + upload 命令；cookie 从 `xhs-publish.json` 导入 |
| `xhs-interact` | 同 xhs-content-ops，浏览域 cookie |
| `douyin-publish` | forked cli 持久化 session `douyin` + upload；有头登录 |
| `weibo-publish` | forked cli 持久化 session `weibo` + upload；有头登录 |
| `zhihu-publish` | forked cli 持久化 session `zhihu` + upload；有头登录 |
| `wechat-channels-publish` | forked cli 持久化 session `wechat-channel` + upload；无头截图 QR 登录 |
| `youtube-publish`（全局 skill） | forked cli 持久化 session `youtube` + upload |
| `wx-mp-hunter` | 见 §6 收编 |
| `wx-mp-publisher` / `wx-mp-engagement` | wx-mp 域，无头截图 QR 登录；engagement 已同步（commit cab3fb3） |
| `xianyu-ops` | forked cli 持久化 session `xianyu`；有头登录 |
| `published-track` | `fetch-and-update-metrics.sh` 内部 login-manager 探活调用改为读新中央存储；浏览器获取流程（zhihu/toutiao/juejin/twitter/youtube/FB/IG/TikTok/Pinterest/Threads）改 forked cli |
| `twitter-interact` | 见 §7 恢复脚本模式 |
| `twitter-post` | forked cli 持久化 session `twitter` + upload（Quote/Reply） |

> 临时性 session（不登录站点）：`rss-reader` / 新闻抓取 / `intel-gathering` 等纯浏览取数，走 forked cli 默认临时 profile，不 cp 模板、不持久化。

---

## 6. wx-mp-hunter 收编

当前 wx-mp-hunter 有单独登录流程（`wx_mp_hunter.ts` 的 `login-qr` / `login-confirm` 两步，cookie 自管，见记忆 `11-heartbeat-isolated-session-gotcha.md`）。

改造：登录走 login-manager 统一流程（wx-mp 无头截图 QR），cookie 落 `~/.openclaw/logins/wx_mp.json`。wx-mp-hunter 只保留抓公众号文章的核心逻辑（搜索/文章列表/正文，参考上游 `wechat-article/wechat-article-exporter`），不再自管登录。

心跳里的 wx_mp 登录死锁问题（记忆 11）随此改造一并消解——login-manager 统一流程 + 心跳约束 4（登录失效跳过等白天处理）。

---

## 7. twitter-interact 恢复脚本模式

**参考项目**：`yikart/AiToEarn`（记忆 `02-upstream-sources.md` 第 4 行，"twitter 互动操作模式"）。

**任务**（下个对话做，本轮不动）：
1. 看 AiToEarn 上游当前 twitter 互动这块的进展（catchup commit `74e884f0` v2.4.0 之后的 HEAD 差异）
2. 照搬其操作模式到 twitter-interact（脚本操作模式，camoufox-cli 持久化 session `twitter` + 中央 cookie/UA）
3. 登录对齐原则 3（twitter 有头登录）

当前 twitter-interact 已经是 camoufox-cli + login-manager 中央 cookie 架构（SKILL.md 已写），主要是对齐 forked cli 的 upload/identity export 新命令 + 跟上游模式。

---

## 8. smart-search 适配

smart-search 是全局 skill（`skills/smart-search/`），针对所有站点。全量切换 forked camoufox-cli 后：
- 涉及登录的站点（自媒体平台）→ 持久化 session（§0 平台列表）
- 不涉及登录的站点（新闻等）→ 临时性 session

smart-search 内部按站点是否需要登录分流到上述两种 session 模式。具体适配范围在调研阶段确认（smart-search 当前对 browser tool / CDP 的依赖面）。

---

## 9. setup-crew.sh 改造

`scripts/setup-crew.sh` 每次**同步代码仓 crew 的 skills 到本地部署实例**：
- ✅ 同步：`crews/<crew-id>/skills/` → `~/.openclaw/crews/<crew-id>/skills/`（覆盖）
- ❌ 不动：本地 `Agents.md` / `Tools.md` / `Memory`（这些本地有自定义内容）
- ❌ 不动：本地部署实例里的自定义 skill（Chrome 的 skill 等本地私货）

> 遵循记忆铁律 `50-code-repo-only-no-touch-local-instance`：setup-crew.sh 是用户明确要求的同步通道，属于"明确要求同步"的例外，但只同步 skill，不碰其他。

---

## 10. profile 丢失处理

profile 丢失 / 损坏 / 指纹错配 → **重建 + 重登录，绝对不允许导入**（补充 D，强化原则 5）。

理由：xhs `a1`/`websectiga` 等设备指纹 cookie 导入到不同指纹会错配 → 被风控检测（见上一轮分析）。任何"用 cookie 造一个登录会话"的动作都禁止（HEARTBEAT.md 约束 4 已写，2026-06-29 CDP 注入 22 cookie 触发风控的教训）。

---

## 11. 落地顺序

1. **调研**（§2.1）：openclaw/extensions/browser 替换接口/兼容层 → 产出 `docs/browser-extension-replacement-research.md`
2. **fork camoufox-cli**（§1）：vendor 进 `patches/camoufox-cli/`，补 upload / fail-first 队列 / identity export
3. **替换 extension**（§2）：按调研结论替换 `openclaw/extensions/browser`，browser-guide 并入
4. **patch 重组**（§3）：删 03/05/06/07，overrides.sh 去 patchright
5. **login-manager 改纯指导**（§4）：删脚本，改写 SKILL.md，同步 4 个 bug fix
6. **平台 skill 逐个改造**（§5）：按表格逐个改
7. **wx-mp-hunter 收编**（§6）
8. **twitter-interact 恢复**（§7）：跟 AiToEarn 上游
9. **smart-search 适配**（§8）
10. **setup-crew.sh 改造**（§9）
11. **README / CHANGELOG / 致谢**：v5.6.0 重磅说明，致谢 Bin-Huang / camoufox-cli（fork 基线）

---

## 12. 未定点（执行时再决）

- twitter-interact op 级 script/browser 取舍细节（跟上游 AiToEarn 后定）
- smart-search 适配的具体范围（调研阶段定）
- forked cli fail-first 队列的超时 / 重试上限（先无超时，agent 自行决策重试）
- 版本号：v5.6.0（CHANGELOG 已记 2026-07-12）vs v6.0（重磅可冲 6.0）——执行时跟用户定
- 上一轮用户被中断的句子"然后目前的patched…"——可能指当前 patchright patched 状态的收尾，已在 §3 patch 重组 + 补充 C 覆盖

---

## 13. 致谢

- **Bin-Huang / camoufox-cli**：fork 基线，本栈整体替换的核心依赖
- AiToEarn（twitter 互动模式）、wechat-article-exporter（wx-mp-hunter）、Spider_XHS（xhs-content-ops）——见记忆 `02-upstream-sources.md`
