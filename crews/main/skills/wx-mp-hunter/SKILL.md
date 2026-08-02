---
name: wx-mp-hunter
description: 微信公众号内容抓取。如下三个场景必用本技能：(1) 用户提供 mp.weixin.qq.com 文章链接 -> 直接用本技能 fetch 全文（不要用浏览器 或 web_fetch）；(2) 用户提供公众号名称、要求获取该账号过去数小时的发布列表 -> 用本技能 posts-list（依赖本机运行的微信客户端容器，使用前检查相关环境变量是否存在，不存在直接报错）；(3) 用户提供 mp.weixin.qq.com/mp/homepage 专题页/主题页链接 或 mp.weixin.qq.com/mp/appmsgalbum 合集链接，要求采集该页面全部文章 -> 用本技能 homepage 采集目录链接（走 camoufox 无头浏览器，不走 HTTP），再逐篇 fetch 抓全文。不支持视频号、评论、互动数据。
metadata:
  openclaw:
    emoji: 📰
    requires:
      bins:
      - python3
---

# WeChat Official Account Hunter (wx-mp-hunter)

Use this skill when:
- The user wants to fetch the full text of a WeChat article by its `mp.weixin.qq.com` URL
- The user wants to list the latest posts of specific Official Accounts over the past N hours
- The user provides a `mp.weixin.qq.com/mp/homepage` topic/homepage URL or `mp.weixin.qq.com/mp/appmsgalbum` album URL and wants to collect article links from that page

**Does NOT support:** WeChat Video Accounts (视频号), comments, or engagement metrics (those require Credentials).

---

## ⚠️ Agent 行为约束（必须遵守）

1. **严格按本 SKILL.md 的步骤执行**，不得在服务器结果未返回时自行编排下一步。
2. **等待服务器响应**：每次执行脚本命令后，必须等待脚本返回 JSON 结果。若结果需要时间，**先向用户说明"正在请求服务器，请稍候……"**，然后等待。
3. **严禁提前假设结果**：不得在脚本输出 JSON 之前就根据假设继续后续步骤。
4. **批量前必须小样本验证**：批量抓全文前，必须先选 1 篇文章 `fetch` 验证链路成功；成功后才能批量。
5. **中间产物归集到专用子目录**：执行过程中产生的任何中间/临时文件（命令输出落盘、解析片段、`_wx*.txt` / `_wx_*.txt` 之类的 scratch 捕获、二维码图片等）**一律写入工作区下的 `wx-mp-hunter-out/` 子目录**，不要散落工作区根目录。脚本本身只输出 JSON 到 stdout，凡需要落盘的中间态由你显式写到该子目录（必要时先 `mkdir -p wx-mp-hunter-out`）。最终交付给用户的文章 JSON/Markdown 也放该子目录。

---

## 两条独立工作流

```
流程 1a：直接获取指定文章内容（URL 来源不限）
  └─ fetch <url>             → 微信客户端 UA 直访拿正文

流程 1b：获取指定账号过去数小时的发布列表
  └─ posts-list [--hours N] [--accounts a,b,c]
                              → 扫本机微信客户端容器消息库
                                （依赖容器环境，使用前检查环境变量）

流程 1c：专题页/主页/合集目录链接采集（mp/homepage 或 mp/appmsgalbum）
  └─ homepage <url>          → camoufox-cli 打开专题页，完整滚动 +
                                分类 tab 采集 mp.weixin.qq.com/s 文章链接
  └─ 对每个链接 fetch <url>   → 逐篇抓全文
```

> **fetch 不需要登录态**：用微信客户端 UA（含 `MicroMessenger`）+ 完整浏览器
> headers + `httpx follow_redirects` 直访文章长链，腾讯风控对该 UA 直接放行
> （302 → `&nwr_flag=1#wechat_redirect` → 正文），零 cookie / 零 captcha。

> **posts-list 不需要登录态**：直接扫本机微信客户端容器内的消息库
> （SQLCipher 加密 + Zstd 压缩），按账号白名单过滤、按时间窗口取过去 N 小时
> 的文章。**仅能拿到容器客户端已登录微信账号已关注的公众号推送**。

> **homepage 不需要登录态**：camoufox-cli 无头打开专题页，完整滚动 +
> 分类 tab 采集 `mp.weixin.qq.com/s` 文章链接。用临时 session，不绑持久化
> profile，不需要任何登录态。

---

## fetch — 获取文章全文

```bash
wx-mp-hunter fetch <url> [--html] [--download-images] [--output-dir <dir>]
```

| Option | Description |
|--------|-------------|
| `url` | 文章链接（`mp.weixin.qq.com`，长链或短链均可） |
| `--html` | 同时返回正文原始 HTML |
| `--download-images` | 把正文图片下载到本地，`content_markdown` 中的图片 URL 替换为本地相对路径 |
| `--output-dir <dir>` | 图片下载目标目录（配合 `--download-images`；默认当前目录） |

输出示例：
```json
{
  "ok": true,
  "url": "https://mp.weixin.qq.com/s/xxxxx",
  "title": "文章标题",
  "author": "公众号名称",
  "publish_time": "2024-03-10",
  "content_text": "正文纯文本内容...",
  "content_markdown": "段落文字……\n\n![](https://mmbiz.qpic.cn/mmbiz_jpg/xxxxx/0?wx_fmt=jpeg)\n\n继续文字……**加粗**……",
  "images": [
    "https://mmbiz.qpic.cn/mmbiz_jpg/xxxxx/0?wx_fmt=jpeg",
    "https://mmbiz.qpic.cn/mmbiz_png/xxxxx/0?wx_fmt=png"
  ]
}
```

| 字段 | 说明 |
|------|------|
| `content_text` | 纯文本正文（去除所有 HTML 标签） |
| `content_markdown` | Markdown 格式正文，图片以内联 `![](url)` 放在原文位置，保留加粗/斜体/链接；`--download-images` 时 URL 替换为 `images/<hash>.<ext>` 本地相对路径 |
| `images` | 正文所有图片 CDN 链接（从 `data-src` 解析） |

### 图片本地化

加 `--download-images --output-dir <dir>` 后，脚本并发下载（默认 4 并发、单图 ≤5MB、总量 ≤100MB）到 `<dir>/images/<hash>.<ext>`，并把 `content_markdown` 里的图片 URL 替换为本地相对路径，便于离线阅读 / 二次加工 / 转存。

```
wx-mp-hunter fetch <url> --html --download-images --output-dir ./article-out
```

---

## posts-list — 获取指定账号过去数小时的发布列表

```bash
wx-mp-hunter posts-list [--hours N] [--accounts a,b,c]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--hours` | 24 | 时间窗口（小时） |
| `--accounts` | "" | 公众号名白名单，逗号分隔；不传则返回全部 |

输出示例：
```json
{
  "ok": true,
  "limit_hours": 24,
  "total": 3,
  "posts": [
    {
      "title": "文章标题",
      "url": "https://mp.weixin.qq.com/s/xxxxx",
      "author": "公众号名称",
      "publish_time": "2024-03-10",
      "cover": "https://..."
    }
  ],
  "missing_accounts": ["某未命中公众号"],
  "hint": "以下账号过去 24h 未在消息库中扫到文章（共 1 个）：某未命中公众号。可能是该公众号在此时间窗口内未发布，也可能是本机微信客户端未关注该公众号。若需稳定接收该公众号推送，请确认本机微信客户端已关注该公众号。"
}
```

### ⚠️ 使用前的环境检查

`posts-list` 依赖本机运行的微信客户端容器。**使用此命令前必须检查以下环境变量是否存在**：

| 环境变量 | 用途 |
|---------|------|
| `WX_BIZ_CONTAINER` | 微信客户端容器名 |
| `WX_BIZ_USER_DIR` | 容器内微信用户数据根目录 |
| `WX_BIZ_KEYS_FILE` | 容器内密钥文件路径 |

如果这些环境变量不存在（或容器未运行），脚本会直接报错退出：
```
{"ok": false, "error": "缺少环境变量 WX_BIZ_CONTAINER：posts-list 依赖本机微信客户端容器，请先在环境中设置该变量指向运行中的容器名"}
```

**重要**：仅 `posts-list` 命令会检查这些环境变量。普通 `fetch` 抓文章不需要这些变量，也不会检查。

### 已关注账号约束

`posts-list` 只能拿到**容器客户端已登录微信账号已关注的公众号**的推送。如果用户要求抓取的账号不在已关注清单中（即消息库中扫不出来），脚本会在 `missing_accounts` 字段列出这些账号，并在 `hint` 字段提示用户：

> 可能是该公众号在此时间窗口内未发布，也可能是本机微信客户端未关注该公众号。若需稳定接收该公众号推送，请确认本机微信客户端已关注该公众号。

遇到这种情况，**告知用户**：需要先在本机微信客户端（容器内已登录的微信账号）关注该公众号，才能通过 `posts-list` 拿到该账号的推送。

---

## homepage — 专题页/主页/合集目录链接采集（mp/homepage 或 mp/appmsgalbum）

触发条件：用户提供类似以下 URL，并要求抓取该页面/专题/合集里的文章：

```text
https://mp.weixin.qq.com/mp/homepage?...
http://mp.weixin.qq.com/mp/homepage?...
https://mp.weixin.qq.com/mp/appmsgalbum?...
http://mp.weixin.qq.com/mp/appmsgalbum?...
```

> `mp/homepage` 是专题页/主题页，`mp/appmsgalbum` 是合集页（album）。两种形态都走
> `homepage` 命令——camoufox-cli 无头浏览器打开，完整滚动 + 分类 tab 采集文章链接，
> **不走 HTTP 直访**（合集页是 JS 渲染的动态列表，HTTP 拿不到完整链接）。

```bash
wx-mp-hunter homepage <url>
```

输出示例：
```json
{
  "ok": true,
  "total": 15,
  "categories": ["全部", "技术", "产品"],
  "links": [
    {"title": "文章标题 1", "url": "https://mp.weixin.qq.com/s/xxxxx"},
    {"title": "文章标题 2", "url": "https://mp.weixin.qq.com/s/yyyyy"}
  ],
  "session": "wx_mp"
}
```

### 目录采集流程

1. **不要直接承诺"已抓完全部文章"**。先说明该页面是微信动态专题页，需要完整滚动加载后统计。
2. 使用 camoufox-cli 打开专题页（headless session，操作要点：snapshot 拿 ref → eval 滚动/提取，别自己 hack selector）。
3. 先执行整页滚动到底，直到 `document.documentElement.scrollHeight` 连续多次稳定。
4. 查找分类 tab（常见 class：`.jsCate`）。对每个分类逐个执行：
   - 点击分类；
   - 等待内容加载；
   - 从顶部滚动到底，直到高度稳定；
   - 提取所有 `a[href*="mp.weixin.qq.com/s"]` 的标题和链接。
5. 合并顶部推荐与各分类结果，按 URL 去重。
6. 向用户报告：分类列表、原始链接数、去重文章数；如果数量明显偏少，继续滚动或请用户确认页面是否还存在折叠/下拉区域。

### 全文采集

1. 拿到 `homepage` 输出的 `links` 列表后，对每个链接走 `fetch`：
   ```bash
   wx-mp-hunter fetch <article_link> --html
   ```
2. 先选 1 篇样本验证，成功后才批量。
3. 批量抓取时每篇间隔 1–2 秒；连续失败 3 篇以上时停止批量，先检查错误，不要继续跑完整列表。
4. 如果样本返回 `未找到文章正文 (#js_content)`，用 camoufox-cli 打开该文章验证页面内容：
   - 如果出现"环境异常""拖动下方滑块完成拼图"等验证页，**不得尝试绕过验证码或自动拖滑块**；告知用户需要人工完成微信环境验证后再继续。
   - 如果是文章已删除、私有或付费，跳过该文章并记录失败原因。

---

## 典型用法示例

**场景 A：直接抓取已知 URL 的文章**
```
1. fetch <url>              → 微信客户端 UA 直访拿正文
```

**场景 B：监控某账号最新文章**
```
1. posts-list --hours 24 --accounts "公众号名"
                              → 扫容器消息库拿过去 24h 该账号的推送
2. 对感兴趣的文章 fetch <article_link>
                              → 抓全文
```

**场景 C：批量获取专题页文章**
```
1. homepage <mp/homepage url>
                              → camoufox 滚动采集专题页文章链接
2. 对每个链接 fetch <article_link>
   pause 1-2s between requests
```

---

## 错误处理

| Error | 原因 | 处理 |
|-------|------|------|
| `UA 直访被风控` (fetch) | 微信客户端 UA 也被风控（罕见） | 重试一次；仍失败跳过该文章 |
| `未找到文章正文 (#js_content)` (fetch) | 文章已删除或私有 | 跳过该文章 |
| `缺少环境变量 WX_BIZ_CONTAINER` (posts-list) | 容器环境未配置 | 报错退出，告知用户需配置环境变量并启动容器 |
| `HTTP 4xx` on fetch | 文章已删除或私有 | 跳过该文章 |
