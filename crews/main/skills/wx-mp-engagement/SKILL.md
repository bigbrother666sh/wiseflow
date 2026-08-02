---
name: wx-mp-engagement
description: 微信公众号 engagement 数据抓取。通过 camoufox-cli 跑创作者中心拿已发布文章的阅读数 / 点赞数 / 评论数 / 分享数 / 收藏数，写入 published-track的 pub_wx_mp 表。
metadata:
  openclaw:
    emoji: 📈
    requires:
      bins:
      - python3
      - camoufox-cli
      - sqlite3
---

# 微信公众号 Engagement 抓取

通过 **camoufox-cli + 本技能自管的 wx_mp 持久化 session + 创作者中心列表页爬虫**，从公众号后台「发表记录」页抓已发布文章的阅读/点赞/评论/分享/收藏，写入 published-track 的 `pub_wx_mp` 表。

**思路**：创作者中心后台的「发表记录」页面把每篇已发布文章的阅读/点赞/评论/分享/收藏列在行内，走「发表记录页 → 解析 innerText → 按标题匹配 → 提行内数字」，不需要打开单篇分析页。

**限制**：仅支持用户**自己有后台权限的号**（创作者中心用公众号账号登录）。竞品号拿不到——这是产品约束，不是技术约束。

---

## 前置条件

### 1. wx_mp session 登录态（本技能自管）

wx-mp-engagement 自管 camoufox 持久化 session `wx_mp`（类似 zhihu-publish / weibo-publish 自管各自平台 session）。camoufox-cli 命令统一 `--session wx_mp --persistent`，登录态在 session profile 里已就位即可，**不导出 cookie/UA/token**。

**登录态判断**（不再会话前探活）：直接 camoufox 打开创作者中心首页，看 redirect URL：
- 跳到 `/cgi-bin/home?...&token=xxx` = 登录就位
- 跳到 `login` / `scanloginqrcode` = 失效，需重登

**失效重登流程**（走本技能自己）：
```bash
wx-mp-engagement login           # camoufox 无头截 QR PNG 落 /tmp/qr-wx-mp.png
# （发 QR PNG 给用户 -> 用户扫码后 -> 主会话回复"已扫码"）
wx-mp-engagement login-confirm   # 验登录就位 + close session（不导出 cookie/UA/token）
```

退出码：
- `0` 成功
- `1` 通用错误（参数错 / row 找不到 / 标题未匹配）
- `2` session 失效（创作者中心首页跳登录页）

### 2. published-track DB 已就位

```bash
ls ~/.openclaw/workspace-main/db/published_track.db
# 初始化（如未建）
~/.openclaw/workspace-main/skills/published-track/scripts/init-db.sh
```

---

## CLI

```bash
# dump 创作者中心 DOM + 截图 + 解析出的文章列表 JSON
wx-mp-engagement probe
# 产物落在 ./wx-mp-engagement-probe/：01_center.png / 02_list.png / 02_list.html / 03_articles.json

# 列出后台所有文章 + 行内 metrics
wx-mp-engagement list

# 抓单篇（按 row.title 在列表页匹配）
wx-mp-engagement fetch --row-id <pub_wx_mp.id>

# 批量抓取最近 N 天未更新（reads=0）的所有 wx_mp 记录
wx-mp-engagement fetch-all --days 7
```

---

## 工作流程

### 关键发现（2026-07-09）

1. **发表记录页 URL**：`https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token=<TOKEN>&lang=zh_CN`
   - 不是 `appmsg?action=list`（那是草稿箱）
   - **必须带 token 参数**，否则显示"请重新登录"

2. **Token 来源**：camoufox 打开首页后从 redirect URL 实时提 token（首页自动重定向到 `/cgi-bin/home?...&token=xxx`）。token 与 wx_mp session 同寿命，失效则一并失效（首页跳登录页 → 走本技能重登流）。

3. **Cookie 导入禁忌**：⚠️ **严禁** `camoufox-cli cookies import` 造会话（浏览器方案严禁 cookie 导入）。本技能自管 `wx_mp` 持久化 session，camoufox-cli 命令统一 `--session wx_mp --persistent`，登录态在 session profile 里已就位，**不开独立 session、不 import cookie**。撞 fail-first 队列（同 session 正被占用）就等占用方完成再串行接力，**不**自动 close 正在跑的 session。

4. **数据提取方式**：不依赖 selector，直接用 `document.body.innerText` 解析。页面 innerText 结构清晰：
   ```
   06月30日
   已发表
   文章标题
   转载/原创/视频号
   <阅读数> <赞> <评论> <分享> <收藏> <在看?> <额外?>
   ```

### fetch 流程

```
1. camoufox 打开创作者中心首页
   ├─ redirect URL 跳 login/scanloginqrcode → exit 2（调用方触发本技能 login + login-confirm）
   └─ redirect URL 跳 /cgi-bin/home?token=xxx → 继续
2. lookup_published_row(row_id) -> 拿 title / publish_url
3. 复用 wx_mp 持久化 session（不开独立 session、不 import cookie）：
   camoufox-cli --session wx_mp --persistent --json open "https://mp.weixin.qq.com/"
4. 读 redirect URL 拿 token（open 首页自动重定向到 /cgi-bin/home?...&token=xxx）：
   camoufox-cli --session wx_mp --json url
5. camoufox-cli --session wx_mp --persistent --json open "https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token=<TOKEN>&lang=zh_CN" -> 发表记录页
6. camoufox-cli --session wx_mp --json eval <innerText 解析 JS> -> [{title, metrics}, ...]
7. match_article(rows, row.title) -> 按标题归一化匹配
8. update-metrics.sh --platform wx_mp --id <row_id> ... -> 写 pub_wx_mp
9. finally: close session（登录态在磁盘 profile，不留进程占内存；下次 fetch 按需重起无头 session，profile 桥接登录态）
```

---

## 输出 JSON 示例

```json
{
  "ok": true,
  "row_id": 42,
  "title": "测试文章",
  "publish_url": "https://mp.weixin.qq.com/s?__biz=xxx&mid=123",
  "session": "wx_mp",
  "metrics": {
    "reads": 576,
    "likes": 10,
    "comments": 16,
    "shares": 6,
    "favorites": 1
  },
  "update": {"ok": true, "action": "updated"}
}
```

---

## 与 published-track 集成

wx_mp 的互动数据抓取**不走** `fetch-and-update-metrics.sh`——后者只管 xhs/bilibili/douyin/kuaishou 四个纯 HTTP+cookie 平台（login-manager 探活 → fetch-retro-data.ts → update-metrics.sh）。wx_mp 走 camoufox 抓创作者中心，机制完全不同，由本 skill 独立承担，agent 直调本 skill wrapper：

```bash
wx-mp-engagement fetch --row-id <rowid>
```

本 skill 内部流程：
1. camoufox 打开创作者中心首页，看 redirect URL 判断登录态（跳登录页 = 失效，exit 2）
2. 从 redirect URL 提 token，camoufox 抓创作者中心发表记录页
3. 解析 innerText 按标题匹配拿 metrics
4. 调 `./skills/published-track/scripts/update-metrics.sh --platform wx_mp --id <rowid> ...` 写 pub_wx_mp

> `update-metrics.sh` 是 published-track 的纯写库脚本，本 skill 写库就走它（不经过 fetch-and-update-metrics.sh）。`fetch-and-update-metrics.sh` 收到 `--platform wx_mp` 会直接 exit 1 报错提示走本 skill，两条链路独立、不耦合。

---

## 约束

- **浏览器方案**：camoufox-cli 主推；不 fork；不 bake chromium
- **并发**：本技能自管 `wx_mp` 持久化 session，fail-first 队列串行接力，不自动 close 正在跑的 session
- **登录态管理**：不导出 cookie/UA/token——登录态在 wx_mp session profile 里就位即可。失效时走本技能 `login` + `login-confirm` 重登（重登后登录态在 profile 里就位），再 camoufox 打开首页拿新 token 拼列表页 URL
- **整块 client 容器内闭环**（不碰 relay）
- **凭据边界**：本 skill 只用浏览器 session token；**不动** `wx-mp-publisher` 的 AppID/AppSecret

---

## Pitfalls

### pitfall: 创作者中心 DOM 改版

- **症状**：innerText 解析返回空或数据错位
- **workaround**：跑 `probe` 命令检查 `02_list.html` 确认页面结构，调整解析逻辑

### pitfall: 抓取频限封号

- **症状**：突然 403 / 风控页
- **workaround**：严格节流——每公众号每天 ≤ 1 次全量；违规立即降级到 manual update

### pitfall: 公众号文章未到 24h 无阅读数

- **症状**：阅读数 0（实际是未刷新）
- **workaround**：不报错，记 0；T+1d 重抓（fetch-all 自动覆盖）

### pitfall: token 过期

- **症状**：列表页显示"请重新登录"
- **workaround**：token 与 wx_mp session 同寿命，失效则 camoufox 打开首页跳登录页 → exit 2 → 走本技能 `login` + `login-confirm` 重登流（重登后登录态在 profile 里就位），再用新 token 拼列表页 URL

### pitfall: 列表页 URL 必须带 token

- **症状**：不带 token 的 URL 显示"请重新登录"
- **workaround**：从 camoufox 打开首页后的 redirect URL 实时提 token（首页自动重定向到 `/cgi-bin/home?...&token=xxx`），再拼列表页 URL

---

## Notes

- **限频建议**：单公众号每 24h 全量 ≤ 1 次；单篇按需触发
- **失败兜底**：本 skill 跑不通时回退到 manual update（`update-metrics.sh --reads ... --likes ... --comments ...` 手动填）
- **camoufox-cli 注意**：本 skill 全部命令统一 `--session wx_mp --persistent`（本技能自管的持久化 session），headless 是默认行为；token 从 session 内 redirect URL 实时拿
