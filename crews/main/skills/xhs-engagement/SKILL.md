---
name: xhs-engagement
description: 抓取小红书已发布笔记的阅读/点赞/收藏/评论/分享数据。通过 camoufox 打开 creator 创作服务平台后台解析互动数，与 published-track 职责边界对齐（本 skill 单纯取数，DB 操作由 published-track 承担）。
metadata:
  openclaw:
    requires:
      bins:
      - python3
      - camoufox-cli
---

# xhs-engagement — 小红书互动数抓取

通过 **camoufox-cli + xhs-browse 持久化 session + creator 创作服务平台后台爬虫**，从创作者后台「笔记管理」页抓已发布笔记的阅读/点赞/收藏/评论/分享。

**思路**：creator 后台笔记管理页把每条已发布笔记的 5 列互动数（阅读/点赞/收藏/评论/分享）列在卡片内，走「打开 creator 后台 → eval 解析 `.note-card__body` → 按 title 匹配 → 提卡片内 5 列数字」。

**为什么不用旧的 profile SSR 方案**：2026-07-25 起小红书把 profile 页 SSR `__INITIAL_STATE__.user.notes` 置空数组（客户端 hydration 才回填），旧方案 `fetchXhsProfileEntries` 解析 SSR HTML 拿到空数组 → `PROFILE_MAPPING_EMPTY`。这是结构性变化，不会回滚。creator 后台方案数据更全（多阅读量）、风控更低（creator 后台是官方管理界面，用户自己每天看的页面）、维护成本更低（DOM 结构稳定，不像 SSR 结构随时变）。

**职责边界**：本 skill 单纯取数——camoufox 打开 creator 后台、解析互动数、返回 JSON。DB 查询/写入由 published-track 承担（`published-track fetch-metrics --platform xhs` 内部委托本 skill 取数，再用 `update-metrics.sh` 写库）。与 wx-mp-engagement 的职责边界对齐。

---

## 前置条件

### 1. 登录态管理（login-manager + creator SSO，本 skill 不自管）

**与 wx-mp-engagement 的关键差异**：wx_mp 的登录态只需留在 camoufox profile 即可；xhs 每次登录**必须导出 cookie+UA** 到中央存储（`xhs-publish` / `viral-chaser` / `xhs-content-ops` 等 raw HTTP 下游消费 `~/.openclaw/logins/xhs-*.json`），所以本 skill **不自管登录**，复用平台级两步登录流程（参考 xhs-publish 的登录态管理）：

| 步骤 | 负责 skill | 产出 |
|------|-----------|------|
| ① www 消费者域登录 | login-manager | `~/.openclaw/logins/xhs-browse.json` + `.ua.json` |
| ② creator 创作者域 SSO | xhs-publish（`login-verify`） | `~/.openclaw/logins/xhs-publish.json` + `.ua.json` |

本 skill 消费的是 **xhs-browse session profile 里的 creator 登录态**（camoufox 打开 creator 后台时 SSO 态在 profile 里就位），自身**不导出任何 cookie**。

**探活**：

```bash
xhs-engagement check
```

- exit 0 = creator 后台登录态就位 → 直接取数
- exit 2 = `SESSION_EXPIRED`（creator 后台跳登录页）→ 走下方重登流程
- exit 1 = crash / 页面异常 → 人工排查（可先跑 `probe` 看页面）

**重登流程**（exit 2 时触发，两步都做——只重登 www 不做 SSO，creator 域 cookie 不会落）：

1. **www 消费者域重登**（走 login-manager 的有头手动登录流程）：
   ```bash
   camoufox-cli --session xhs-browse --persistent --headed --json open "https://www.xiaohongshu.com/"
   # 通知用户在窗口里手动扫码登录，等用户确认完成
   login-manager --platform xhs-browse   # 导出+两层探活验证，过了才 commit xhs-browse.json + UA
   ```
   有头显示环境纪律（DISPLAY 继承、不手动设 DISPLAY、不自起 Xvfb）见 login-manager SKILL.md Step 0。

2. **creator 创作者域 SSO**（www 已登录 → 自动 SSO，无需扫码）：
   ```bash
   xhs-publish login-verify
   ```
   脚本闭环（共享 session=xhs-browse）：自检 web_session → open creator SSO 页自动重定向 → 轮询创作者 cookie 落盘 → `personal_info` 裸 GET 验过才 commit `xhs-publish.json` + UA → close session。SSO 未完成 / 验证不过 exit 2、不重试。

两步完成后 `xhs-engagement check` 应回 exit 0。

### 2. camoufox-cli daemon idle 自退约束

forked camoufox-cli 有全局硬上限 `MAX_IDLE_TIMEOUT = 60`（`patches/camoufox-cli/src/server.ts`）：任何 session（包括 `--persistent`）idle 超过 60s 就自退。这是防浏览器进程堆积的后备闸。

**对本 skill 的约束**：camoufox 打开 creator 后台后，**必须在 60s 内发完所有 eval 命令**，否则 daemon 自退、page 没了。本 skill 实现是「open → 立即连续 eval → close」一条龙，不跨 60s 窗口。

---

## CLI

```bash
# 判 creator 后台登录态（取数前探活用）
xhs-engagement check

# 抓单条笔记互动数（按 title 在 creator 后台笔记列表匹配）
xhs-engagement fetch --title "笔记标题"

# 列出 creator 后台所有笔记 + 5 列互动数
xhs-engagement list

# dump creator 后台 DOM + 截图 + 解析出的笔记列表 JSON（调试用）
xhs-engagement probe
```

---

## 工作流程

### fetch 流程

```
1. camoufox 打开 creator 后台笔记管理页（复用 xhs-browse session 登录态）
   URL: https://creator.xiaohongshu.com/new/note-manager?source=official
   ├─ 跳登录页 → exit 2（SESSION_EXPIRED，走重登流程）
   └─ 正常显示笔记卡片 → 继续
2. 等待 `.note-card__body` 元素出现（最多 15s）
3. eval 解析所有 `.note-card__body`，提取：
   - 标题：`.note-card__title`
   - 5 列互动数：`.note-card__row--stats .note-card__stat span`
     顺序：[0]阅读量 [1]点赞数 [2]收藏数 [3]评论数 [4]分享数
4. 按 title 匹配目标笔记（normalize 后精确匹配，其次唯一前缀互含防截断）
5. close session
6. 输出 JSON
```

### 注意点

1. **creator 后台笔记管理页 URL**：`https://creator.xiaohongshu.com/new/note-manager?source=official`
   - 不是 `https://www.xiaohongshu.com/user/profile/{user_id}`（那是消费者端 profile 页，SSR 已失效）
   - creator 后台是官方创作服务平台，用户自己管理笔记的页面

2. **5 列互动数顺序**：creator 后台笔记管理页 stats 区 5 列数字顺序为 **阅读量 / 点赞数 / 收藏数 / 评论数 / 分享数**。这是小红书创作者后台的标准指标顺序。

3. **title 匹配**：creator 后台方案按 `--title` 匹配目标笔记。`fetch-and-update-metrics.sh` 会自动从 DB 取该行 title 透传。笔记不在 creator 后台列表 → `NOTE_NOT_IN_CREATOR_BACKEND`。

4. **Cookie 导入禁忌**：⚠️ **严禁** `camoufox-cli cookies import` 造会话（浏览器方案严禁 cookie 导入）。本 skill 复用既有 `xhs-browse` 持久化 session，camoufox-cli 命令统一 `--session xhs-browse --persistent`，登录态在 session profile 里已就位，**不开独立 session、不 import cookie**。

5. **数据提取方式**：不依赖 innerText（creator 后台 innerText 结构复杂），直接用 DOM selector 解析。页面 DOM 结构清晰：
   ```
   .note-card
     .note-card__body
       .note-card__row.note-card__row--header
         .note-card__title  → 笔记标题
       .note-card__row.note-card__row--stats
         .note-card__stat (×5)
           span  → 互动数
   ```

---

## 输出 JSON 示例

```json
{
  "ok": true,
  "platform": "xhs",
  "title": "测试笔记",
  "matched_title": "测试笔记",
  "metrics": {
    "views": 11,
    "likes": 0,
    "collects": 0,
    "comments": 0,
    "shares": 0
  }
}
```

失败时：

```json
{
  "ok": false,
  "platform": "xhs",
  "error": "NOTE_NOT_IN_CREATOR_BACKEND",
  "msg": "creator 后台未匹配到该笔记"
}
```

退出码：
- `0` 成功
- `1` 通用错误（参数错 / 标题未匹配 / 解析失败）
- `2` session 失效（creator 后台跳登录页）→ 走「重登流程」

---

## 与 published-track 集成

xhs 的互动数据抓取走本 skill（camoufox 打开 creator 后台），不走 `fetch-retro-data.ts` 的纯 HTTP 链路。

published-track 的 `fetch-retro-data.ts` xhs 分支 `execFile` 调本 skill 的 PATH wrapper：

```
fetch-retro-data.ts --platform xhs --title <title>
  → execFile xhs-engagement fetch --title <title>
  → 拿回 JSON {ok, metrics: {views, likes, collects, comments, shares}}
  → exit 2 透传为 SESSION_EXPIRED
  → 返回 RetroResult
```

DB 写入仍由 published-track 的 `update-metrics.sh` 统一承担（本 skill 不碰 DB）。

---

## Pitfalls

### pitfall: creator 后台 DOM 改版

- **症状**：eval 解析返回空或数据错位
- **workaround**：跑 `probe` 命令检查 `01_note_manager.png` / `01_note_manager.html` / `02_notes.json` 确认页面结构，调整解析逻辑

### pitfall: 抓取频限封号

- **症状**：突然 403 / 风控页
- **workaround**：严格节流——每账号每天 ≤ 1 次全量；违规立即降级到 manual update

### pitfall: 笔记不在 creator 后台列表

- **症状**：`NOTE_NOT_IN_CREATOR_BACKEND`
- **workaround**：creator 后台默认显示全部笔记，但若笔记已删除/审核未通过/私密，不会出现在列表里。检查笔记状态。

### pitfall: camoufox-cli daemon idle 自退

- **症状**：camoufox 打开 creator 后台后，eval 返回「session not found」或「page not found」
- **workaround**：forked camoufox-cli 有全局硬上限 `MAX_IDLE_TIMEOUT = 60`，idle 超过 60s 就自退。本 skill 实现是「open → 立即连续 eval → close」一条龙，不跨 60s 窗口。

### pitfall: 只重登 www 没做 creator SSO

- **症状**：`login-manager --platform xhs-browse` 成功后 `check` 仍 exit 2（creator 后台跳登录页）
- **workaround**：重登流程是两步——www 重登后**必须**再跑 `xhs-publish login-verify` 做 creator SSO，creator 域 cookie 才会落进共享 profile。

---

## Notes

- **限频建议**：单账号每 24h 全量 ≤ 1 次；单篇按需触发
- **camoufox-cli 注意**：本 skill 全部命令统一 `--session xhs-browse --persistent`（复用既有持久化 session），headless 是默认行为
- **报错约束**：调用方（agent）报告失败时必须原样转述脚本 stderr + exit code，禁止根据 DB 字段自行归因
