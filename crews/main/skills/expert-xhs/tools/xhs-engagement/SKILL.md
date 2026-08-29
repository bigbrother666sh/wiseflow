---
name: xhs-engagement
description: 抓取小红书已发布笔记的阅读/评论/点赞/收藏/分享数据，写入 published-track 的 pub_xhs 表。
---

# xhs-engagement — 工具说明

> 本文是 `expert-xhs` 专家包内的工具说明书，不独立出现在技能列表中。由相关 Workflow（数据复盘 / 每日采集）与 HEARTBEAT 指引调用。

**用途**：抓取自己账号已发布小红书笔记的 5 列互动数（阅读/评论/点赞/收藏/分享），写入 published-track 的 `pub_xhs` 表。
**输入**：`pub_xhs` 行 id（`fetch --row-id`）或笔记标题（`fetch --title`）；批量刷新无参数（`fetch-all`）。
**输出**：JSON（互动数 + 写库结果）。

通过 **camoufox-cli + xhs-browse 持久化 session + creator 创作服务平台后台爬虫**，从创作者后台「笔记管理」页抓已发布笔记的阅读/评论/点赞/收藏/分享。

**思路**：creator 后台笔记管理页把每条已发布笔记的 5 列互动数（阅读/评论/点赞/收藏/分享）列在卡片内，走「打开 creator 后台 → eval 解析 `.note-card__body` → 按 title 匹配 → 提卡片内 5 列数字」。

**限制**：仅支持用户**自己有后台权限的号**（视频号助手用微信扫码登录）。竞品号拿不到——这是产品约束，不是技术约束。

---

## 前置条件

### 1. 登录态管理（共享 xhs-browse profile，创作者 cookie 自管）

本工具的登录流程完全走 `xhs-publish` 工具的登录态管理章节。

本工具消费的是 **xhs-browse session profile 里的 creator 登录态**（camoufox 打开 creator 后台时 SSO 态在 profile 里就位），自身**不需要导出任何 cookie**。

每次执行前的探活使用自己的脚本命令。

**探活**：

```bash
xhs-engagement check
```

- exit 0 = creator 后台登录态就位 → 直接取数
- exit 2 = `SESSION_EXPIRED`（creator 后台跳登录页）→ 走下方重登流程
- exit 1 = crash / 页面异常 → 人工排查（可先跑 `probe` 看页面）

**重登流程**（exit 2 时触发，使用 `xhs-publish` 的登录流程）：

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

### 2. camoufox-cli daemon 生命周期

forked camoufox-cli 自 2026-08-22 起**默认不再 idle 自退**（`--timeout` 默认 0）。旧版有 60s 硬上限，会把等用户扫码/交互的 daemon 误杀掉，已移除；防浏览器进程堆积的兜底改为全局并发 daemon 上限 6（超了驱逐最老的）。

**对本工具的约束**：保持「open → 立即连续 eval → close」一条龙——这仍是最高效、最不易撞风控的做法；用完必须 close，不要依赖驱逐兜底。

---

## CLI

```bash
# 判 creator 后台登录态（取数前探活用）
xhs-engagement check

# 抓单条笔记互动数并写库（从 pub_xhs 取该行 title 匹配 → update-metrics.sh 写库）
xhs-engagement fetch --row-id <pub_xhs.id>

# 批量刷新（HEARTBEAT定时任务用）：打开笔记管理页首页一次，解析页内全部笔记，
# 匹配 pub_xhs 全部行写库；不翻页，首页没有的行报 NOT_ON_FIRST_PAGE 跳过
xhs-engagement fetch-all

# 纯取数调试入口（按 title 匹配，只输出 JSON 不写库）
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
0.（--row-id 模式）从 pub_xhs 查该行 title / publish_url
1. camoufox 打开 creator 后台笔记管理页（复用 xhs-browse session 登录态）
   URL: https://creator.xiaohongshu.com/new/note-manager?source=official
   ├─ 跳登录页 → exit 2（SESSION_EXPIRED，走重登流程）
   └─ 正常显示笔记卡片 → 继续
2. 等待 `.note-card__body` 元素出现（最多 15s）
3. eval 解析所有 `.note-card__body`，提取：
   - 标题：`.note-card__title`
   - 5 列互动数：`.note-card__row--stats .note-card__stat span`
     顺序：[0]阅读量 [1]评论数 [2]点赞数 [3]收藏数 [4]分享数
4. 按 title 匹配目标笔记（normalize 后精确匹配，其次唯一前缀互含防截断）
5. close session
6.（--row-id 模式）委托 published-track 的 update-metrics.sh 写 pub_xhs
   （collects 写 favorites 列）
7. 输出 JSON
```

### 注意点

1. **creator 后台笔记管理页 URL**：`https://creator.xiaohongshu.com/new/note-manager?source=official`
   - 不是 `https://www.xiaohongshu.com/user/profile/{user_id}`（那是消费者端 profile 页，SSR 已失效）
   - creator 后台是官方创作服务平台，用户自己管理笔记的页面

2. **5 列互动数顺序**：creator 后台笔记管理页 stats 区 5 列数字顺序为 **阅读量 / 评论数 / 点赞数 / 收藏数 / 分享数**。

3. **首页即窗口，不翻页**：笔记管理页打开就是第一页，`fetch` / `fetch-all` 都只解析首页。页内有什么解析什么——匹配上的写库，匹配不上的（老作品超出首页范围）报 `NOT_ON_FIRST_PAGE` 跳过，**这是设计不是遗漏**。少操作一次页面就少一次风控暴露，**不要加翻页逻辑**。

4. **title 匹配**：creator 后台方案按 title 匹配目标笔记。`fetch --row-id` 会自动从 DB 取该行 title；`fetch --title` 是纯取数调试入口（不写库）。笔记不在 creator 后台列表 → `NOTE_NOT_IN_CREATOR_BACKEND`。

5. **Cookie 导入禁忌**：⚠️ **严禁** `camoufox-cli cookies import` 造会话（浏览器方案严禁 cookie 导入）。本工具复用既有 `xhs-browse` 持久化 session，camoufox-cli 命令统一 `--session xhs-browse --persistent`，登录态在 session profile 里已就位，**不开独立 session、不 import cookie**。

6. **数据提取方式**：不依赖 innerText（creator 后台 innerText 结构复杂），直接用 DOM selector 解析。页面 DOM 结构清晰：
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

`fetch --row-id`（含写库结果）：

```json
{
  "ok": true,
  "platform": "xhs",
  "title": "测试笔记",
  "matched_title": "测试笔记",
  "metrics": {
    "views": 11,
    "comments": 0,
    "likes": 0,
    "collects": 0,
    "shares": 0
  },
  "row_id": 42,
  "publish_url": "https://www.xiaohongshu.com/explore/xxx",
  "update": {"ok": true}
}
```

`fetch --title`（纯取数，无 row_id/update 字段）：

```json
{
  "ok": true,
  "platform": "xhs",
  "title": "测试笔记",
  "matched_title": "测试笔记",
  "metrics": {"views": 11, "comments": 0, "likes": 0, "collects": 0, "shares": 0}
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

xhs 的互动数据抓取由本工具独立承担（camoufox 打开 creator 后台），**不走** `fetch-and-update-metrics.sh`——后者只管 bilibili/douyin/kuaishou 三个纯 HTTP+cookie 平台，收到 `--platform xhs` 会直接 exit 1 报错提示走本工具（与 wx_mp/wx_channel 同模式，两条链路独立、不耦合）。

agent 直调本工具 wrapper：

```bash
xhs-engagement fetch --row-id <rowid>
```

本工具内部流程：
1. 从 pub_xhs 查该行 title / publish_url
2. camoufox 打开 creator 后台笔记管理页判登录态（跳登录页 = 失效，exit 2）
3. eval 解析笔记卡片，按 title 匹配拿 5 列互动数
4. 委托 published-track 的 `update-metrics.sh`，以 `platform=xhs`、`id=<rowid>` 写 pub_xhs（collects 写 favorites 列）

> `update-metrics.sh` 是 published-track 的纯写库脚本，本工具写库就走它（不直接 SQL 写）。

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

### pitfall: camoufox-cli daemon 中途消失

- **症状**：camoufox 打开 creator 后台后，eval 返回「session not found」或「page not found」
- **workaround**：2026-08-22 起已默认关闭 idle 自退，但 daemon 仍可能被并发上限（6 个）驱逐或被 `close --all` 收尾误伤。本工具实现是「open → 立即连续 eval → close」一条龙，缩短 daemon 暴露窗口。

### pitfall: 只重登 www 没做 creator SSO

- **症状**：`login-manager --platform xhs-browse` 成功后 `check` 仍 exit 2（creator 后台跳登录页）
- **workaround**：重登流程是两步——www 重登后**必须**再跑 `xhs-publish login-verify` 做 creator SSO，creator 域 cookie 才会落进共享 profile。

---

## Notes

- **限频建议**：单账号每 24h 全量 ≤ 1 次；单篇按需触发
- **camoufox-cli 注意**：本工具全部命令统一 `--session xhs-browse --persistent`（复用既有持久化 session），headless 是默认行为
- **报错约束**：调用方（agent）报告失败时必须原样转述脚本 stderr + exit code，禁止根据 DB 字段自行归因
