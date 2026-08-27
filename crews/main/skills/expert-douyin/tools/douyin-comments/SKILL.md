---
name: douyin-comments
description: 抓取抖音视频的评论列表（纯 HTTP + cookie + 签名，不起浏览器），输出 JSON 与按点赞排序的 markdown 摘要。
metadata:
  openclaw:
    emoji: 💬
    requires:
      bins:
      - node
---

# douyin-comments — 工具说明

> 本文是 `expert-douyin` 专家包内的工具说明书，不独立出现在技能列表中。由相关 Workflow 指引调用。

抓取指定抖音视频的评论，供对标分析、起号标签反推、评论动机解读使用。

**输入**：视频 `aweme_id` 或视频链接（支持 `v.douyin.com` 短链，自动展开）。
**输出**：JSON（stdout，含评论全文、点赞数、回复数、用户昵称、IP 属地、日期）；`--output` 时额外落一份按点赞降序的 markdown 摘要。

登录态复用中央存储导出的 douyin cookie + UA（与 `douyin` 持久化 session 同一登录态），纯 HTTP 请求，不启动浏览器。

## 使用方式

```bash
# 按 aweme_id 抓（默认前 40 条热度评论）
douyin-comments fetch --aweme-id 7389012345678901234

# 按链接抓 + 落摘要文件
douyin-comments fetch \
  --url "https://www.douyin.com/video/7389012345678901234" \
  --limit 60 \
  --output douyin_ref/dna-0/comments/sample-1.comments.md
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--aweme-id` / `--url` | 二选一；`--url` 支持短链，自动展开解析 |
| `--limit` | 抓取条数上限，1-200（上限是防批量请求触风控），默认 40 |
| `--output` | 可选；写入按点赞降序的 markdown 摘要，路径由调用方指定 |

返回 JSON 主要字段：

```json
{
  "ok": true,
  "awemeId": "...",
  "total": 1234,
  "fetched": 40,
  "truncated": true,
  "comments": [
    {"cid": "...", "text": "...", "likeCount": 89, "replyCount": 3, "userName": "...", "ipLabel": "...", "createTime": "2026-08-01"}
  ]
}
```

## 必做约束

- 只读抓取，不发表、不点赞、不回复任何评论。
- 单次任务批量抓多条视频评论时逐条串行调用，控制总条数（每条 ≤ `--limit`），避免批量请求触风控。
- 评论文本是用户原话，分析时按动机归类（喜欢内容价值 / 喜欢人物状态 / 喜欢形式设定 / 提出具体问题 / 非恶意吐槽），不要把评论数直接当内容质量。

### Exit codes

| code | 含义 | 调用方动作 |
|------|------|-----------|
| `0` | 抓取成功（`truncated=true` 表示达到 limit 或分页中断，未抓全） | 继续分析 |
| `1` | 参数错 / 网络错 / 签名不可用（stderr 有原因） | 排查后重试；签名不可用交 IT engineer 配凭证 |
| `2` | `SESSION_EXPIRED`——cookie 缺失或失效 | 走 `login-manager --platform douyin` 有头重登后重试 |
