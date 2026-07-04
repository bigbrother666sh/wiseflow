---
name: login-manager
description: Manage platform login state (cookies) for Douyin, Bilibili, Kuaishou,
  XHS, and other platforms. Stores cookies locally and handles re-login via browser
  tool when session expires.
metadata:
  openclaw:
    emoji: 🔑
    requires:
      bins:
      - node
---

# Login Manager（平台登录态管理）

Use this skill **before** calling any skill that requires platform cookies (viral-chaser etc.). It ensures valid cookies are available, performing browser-based re-login automatically if needed.

> 📍 **全局技能路径提示**：文中所有 `./scripts/` 路径均相对于本技能所在目录（即 `<skill>` 标签 `location` 属性所指目录），**不是**工作区目录。执行时按本技能实际安装路径拼接。
>
> **⚠️ exec 调用方式**：通过 exec 工具调用时，**不要用 `cd <技能目录> && ./scripts/xxx.sh` 这种复合形式**（会触发 `exec denied: allowlist miss`）。openclaw 加载本技能时已在顶部注入技能的绝对路径，直接把它和 `scripts/xxx.sh` 拼成**完整绝对路径**作为 command 传给 exec 即可。

---

## Storage Location

All platform sessions are stored at:

```
~/.openclaw/logins/{platform}.json
```

File format:

```json
{
  "platform": "douyin",
  "cookies": "sessionid=xxx; token=yyy; ...",
  "user_agent": "Mozilla/5.0 ...",
  "updated_at": "2026-04-11T10:30:00+08:00"
}
```

Supported platform values: `douyin` | `bilibili` | `kuaishou` | `xhs-publish` | `xhs-browse` | `weibo` | `zhihu` | `wechat-channels`

> **小红书双平台说明**：小红书的浏览/互动和发布使用不同的 cookie 域，因此拆为两个独立平台：
> - `xhs-publish`：创作者平台（`creator.xiaohongshu.com`），用于发布笔记/视频。探活 URL：`https://creator.xiaohongshu.com/publish/publish?source=official`
> - `xhs-browse`：消费者端（`www.xiaohongshu.com`），用于搜索、浏览、互动。探活 URL：`https://www.xiaohongshu.com/`

---

## CLI Script

All probe and read/write operations go through the script:

```bash
./scripts/login-manager.sh check  <platform>   # Probe: cookies still valid?
./scripts/login-manager.sh read   <platform>   # Print stored session JSON
./scripts/login-manager.sh write  <platform>   # Save session from stdin JSON
./scripts/login-manager.sh status-all          # Check all stored sessions at once
```

Exit codes:
- `0` — success (cookies valid / operation complete)
- `1` — general error
- `2` — session expired or missing → trigger browser login flow

---

## Usage

### Check session validity

```bash
./scripts/login-manager.sh check <platform>
```

The script:
1. Reads `~/.openclaw/logins/{platform}.json`
2. If missing / empty → exit 2
3. Sends a probe request to the platform API with stored cookies
4. If probe succeeds → prints `{ "ok": true, "cookies": "...", "user_agent": "..." }` to stdout
5. If probe fails → exit 2

**Agent workflow on exit code 2（需要重新登录）：**

1. 使用浏览器工具打开对应平台登录页（**新标签页**）：
   | Platform | Login URL |
   |----------|-----------|
   | douyin   | `https://www.douyin.com/` |
   | bilibili | `https://www.bilibili.com/` |
   | kuaishou | `https://www.kuaishou.com/` |
   | xhs-publish | `https://www.xiaohongshu.com/` → 登录后导航到 `https://creator.xiaohongshu.com/publish/publish?source=official` |
   | xhs-browse | `https://www.xiaohongshu.com/` |
   | weibo    | `https://weibo.com/` |
   | zhihu    | `https://www.zhihu.com/` |
   | wechat-channels | `https://channels.weixin.qq.com/` |
2. 遵循 **browser-guide** skill 完成登录（优先 QR code，次选 SMS / 密码）
3. 登录成功后，**通过 CDP 导出 cookies 并保存**（⚠️ 不可用 `document.cookie`，httpOnly cookie 如 `web_session` 无法通过 JS 访问）：
   1. 执行 `browser action=tabs` 获取标签页列表
   2. 找到已登录平台的标签页，复制其 `wsUrl` 字段
   3. 一步完成 cookie 提取 + UA 获取 + 写入存储：
      ```bash
      ./scripts/export-cookies.sh <wsUrl> <domain> <platform>
      ```
      - `wsUrl`：上一步获取的 CDP WebSocket URL
      - `domain`：平台域名过滤（如 `xiaohongshu.com`、`douyin.com`）
      - `platform`：存储平台名（如 `xhs-publish`、`douyin`）
   4. 脚本成功后输出 `{"ok": true, "platform": "...", "cookieCount": N}`，session 已自动写入 `~/.openclaw/logins/{platform}.json`
4. 关闭登录标签页，重新执行 `check`
5. 若仍失败，告知用户并停止 — **禁止重复登录超过 1 次**

### Check all sessions at once

```bash
./scripts/login-manager.sh status-all
```

Scans `~/.openclaw/logins/` for all stored sessions, probes each, and prints a summary:

```
[login-manager] 登录态总览：3 有效 / 1 过期 / 4 总计

  ✅ douyin (更新于 2026-06-15T10:30:00)
  ✅ bilibili (更新于 2026-06-14T08:00:00)
  ❌ weibo (更新于 2026-05-01T12:00:00)
  ✅ xhs (更新于 2026-06-15T09:00:00)
```

Returns JSON with per-platform status.

### Read session (for other skills)

```bash
./scripts/login-manager.sh read <platform>
```

Prints stored session JSON to stdout. Exit 2 if not found.

---

## Integration with other skills

When a skill requires platform cookies, the pattern is:

```
1. Run: login-manager.sh check <platform>
2. Parse stdout JSON → extract cookies and user_agent
3. Use cookies in subsequent API calls
4. If any API returns auth error (HTTP 401/403 or platform-specific failure):
   - Execute the browser-based re-login workflow (see "Agent workflow on exit code 2" above)
   - Retry the original operation once
   - If still failing, report to the user and stop
```

---

## Notes

- **Do not retry login more than once automatically** — frequent retries risk account suspension (per browser-guide guidelines)
- **QR code login is preferred** for Douyin and Kuaishou — ask user to scan with their mobile app
- **Bilibili** public video access often works without cookies; only request login if the video is unavailable
- **Never store cookies in code or logs** — the session files are stored only in `~/.openclaw/logins/`

## 浏览器操作最佳实践

### 超时错误处理

遇到 `browser failed: timed out` 或类似超时错误时：

- **不需要重启浏览器**，也不执行 `browser stop/start`
- 等待 **30 秒**后在原页面继续操作
- 若仍无法操作，再等 30 秒
- 只有关闭浏览器后重开仍报错才是真正出错，需停止并反馈用户

### 表单输入规范

填写用户名、密码或其他表单内容时：

- 使用 `browser act` 的 `type` 动作，并设置 `slowly: true`
- **不要使用 `fill()`**，可能导致编辑器无法识别内容
- 示例：
  ```
  browser act kind=type ref=<input_ref> text="用户名" slowly=true
  ```
