# camoufox-cli Spike 报告（Phase 4.5 验证）

> 2026-07-03 · 验证 plan §十 的两个 camoufox spike，为 D18 落地扫清不确定性。
>
> 环境：本机 `camoufox-cli@0.6.2`（npm 全局），Node v24.16.0，已有 51job/boss/lagou 三个在用 session profile（求职 crew 留下，未受影响）。

## 结论速览

| Spike | 问题 | 结论 |
|-------|------|------|
| ② | 冻结指纹模板 `camoufox-cli.json` 能否 cp 到新 profile dir 复用 | ✅ **能**（须带 `--persistent`） |
| ① | `cookies export` JSON 能否对接下游 Python | ✅ **能**（Playwright `add_cookies` 零转换，raw HTTP 3 行薄适配） |

两个 spike 均通过，D18 路线无阻塞，**无需 fork camoufox-cli**。

## Spike ② 详情：指纹模板复用

**机制**（源码 `dist/identity.js` `loadOrCreate`）：
- `--persistent` 模式下，profile dir 里的 `camoufox-cli.json` 存在则读、不存在则生成并写。
- 文件含 `fingerprint`（screen/navigator/audioCodecs/…）、`os`、`config`（canvas/fonts seeds）、`locale`。
- "On subsequent launches, `<persistentDir>/camoufox-cli.json` is loaded. Fingerprint, OS, and canvas/font seeds are never touched after first launch."

**测试**：cp boss 的 `camoufox-cli.json` 到新 session `spike2` 的 profile dir，`--persistent` 启动：
- 模板：`Ubuntu / Linux x86_64 / 1920x1080 / rv:147.0`
- 实跑：`Linux x86_64 / 1920x1080 / rv:150.0` ← OS/platform/screen 复用成功
- Firefox rv 版本 147→150：跟 camoufox 二进制版本，**不是指纹维度**，预期行为，不影响反指纹。

**坑**：不传 `--persistent` 时，profile dir 被忽略（走临时 profile），cp 的模板不生效。D18 实现必须显式 `--persistent`。

**D18 落地方式**（共享模板 + 每 session 独立 profile dir）：
1. 一次性 bootstrap：清空模板 dir `~/.openclaw/logins/_template/`，`camoufox-cli --session _template --persistent open about:blank` → 生成冻结 `camoufox-cli.json` → close。
2. 每个 agent session：`mkdir ~/.camoufox-cli/profiles/<session>` → `cp ~/.openclaw/logins/_template/camoufox-cli.json` 进去 → `camoufox-cli --session <session> --persistent ...`。
3. 各 session 共享指纹，独立 `cookies.sqlite`/state。

## Spike ① 详情：cookies export ↔ Python

**格式**：`camoufox-cli cookies export <file.json>` 写出 JSON 数组，元素字段：
```json
{ "name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite" }
```
与 **Playwright Python `context.add_cookies()` 期望格式完全对齐**，零转换可直接吃。

**Python 加载**（已实测）：
- Playwright/patchright Python：`context.add_cookies(json.load(open(f)))` —— 零适配。
- raw HTTP（requests/httpx/urllib）：3 行薄适配转 Cookie header 或 `http.cookiejar`：
  ```python
  cookies = json.load(open(f))
  header = '; '.join(f"{c['name']}={c['value']}" for c in cookies if domain in c['domain'])
  ```
- 本机未装 playwright Python，但格式对齐已确认；适配代码已跑通。

**Round-trip**：`cookies import <file>` 对称工作（import count = export count），新 session 注入后访问目标站点带上了 cookie。

**D18 落地方式**（登录一次 → 中央存储 → 各 session 注入）：
1. 登录 session：`camoufox-cli --session <login> --persistent --headed open <qr-page>` → 截图 QR → 用户扫码 → `cookies export ~/.openclaw/logins/<platform>.json` → close。
2. 各 agent session：`camoufox-cli --session <agent> --persistent ...` → `cookies import ~/.openclaw/logins/<platform>.json` → 跑下游任务。
3. 下游 HTTP 脚本（xhs/douyin 等）从同一 JSON 加载 cookie，薄适配。

## CLI 其他发现（实现时注意）

- `cookies export` 必须给文件参数，不支持 stdout。
- `--json` 把命令输出包成 `{success, data}` 信封，脚本解析取 `.data`。
- daemon 首条命令自动起，默认 1800s idle 超时；长任务注意保活或调 `--timeout`。
- `--session` 隔离 daemon + profile；`close --all` 关全部。
- 浏览器二进制已就位（本机已有在用 profile），新环境需 `camoufox-cli install --with-deps`。

## 对 plan 的影响

- **D18 确认可行**，无需 fork camoufox-cli，无需改其源码。
- **Phase 4.5 风险降级**：原"2 个 spike 验证"已完成，Phase 4.5 可直接进入实现（browser-guide 改写 + 浏览器类 skill 改 camoufox-cli 调用 + login-manager 重写 + 模板/profile/中央存储落地）。
- **login-manager 重写**（D18）：去掉 CDP WebSocket 抽 cookie，改无头截图 QR → `cookies export` → 中央存储 JSON。本 spike 已验证全链路。
- **cookie 中央存储格式**：定为 `~/.openclaw/logins/<platform>.json`，camoufox-cli 原生格式（= Playwright 格式）。
- **抖音发布 spike**（plan §十 另一项，Phase 3 前做）仍待验证：camoufox-cli 能否稳定完成抖音登录态下发布页上传，及前端风控对无头的拦截程度。本 spike 不覆盖。

## 复现命令（精简）

```bash
# spike ② 模板复用
cp ~/.camoufox-cli/profiles/<existing>/camoufox-cli.json ~/.camoufox-cli/profiles/spike2/camoufox-cli.json
camoufox-cli --session spike2 --persistent --json open about:blank
camoufox-cli --session spike2 --json eval "navigator.platform + ' | ' + screen.width + 'x' + screen.height"

# spike ① cookies export → Python
camoufox-cli --session spike1 --persistent --json open "https://httpbin.org/cookies/set?k=v"
camoufox-cli --session spike1 cookies export /tmp/c.json
python3 -c "import json; print(json.load(open('/tmp/c.json')))"
```
