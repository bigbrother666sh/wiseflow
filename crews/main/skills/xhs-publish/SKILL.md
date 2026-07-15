---
name: xhs-publish
description: Publish image-text notes and video notes to Xiaohongshu (小红书) via
  creator COS upload + web_api v2. Supports image posts (up to 18 images),
  video posts, topics/hashtags. Self-managed creator-domain login + 探活 (see 登录态管理).
metadata:
  openclaw:
    emoji: 📕
    requires:
      bins:
      - python3
---

# 小红书发布（xhs-publish）

通过 creator 平台 COS 上传 + `/web_api/sns/v2/note` 创建笔记，支持图文和视频。cookie 认证由本技能**自管**（创作者域登录 + 探活，不进 login-manager）。签名走 relay sign 服务。

上传流程：① 取 COS 上传许可证 `creator.xiaohongshu.com/api/media/v1/upload/web/permit` → ② PUT 文件到 COS（大文件自动分片）→ ③ 创建笔记 `edith.xiaohongshu.com/web_api/sns/v2/note`。

---

## 登录态管理（本技能自管，不进 login-manager）

xhs-publish cookie 是创作者域 `creator.xiaohongshu.com` 会话，与 xhs-browse 消费者域是两套独立登录、不能共用，且仅供本技能使用，故登录 + 探活在本技能内闭环。探活走创作者域 `personal_info` **裸 GET**，无需 xhs 签名 / OFB_KEY。

### Step 1 — 发布前探活（批量发布只探活一次）

```bash
xhs-publish check
```

- exit 0 = 有效 → 继续发布
- exit 2 = `SESSION_EXPIRED` → 走 Step 2 重登，再探活一次
- exit 1 = crash → 人工排查

### Step 2 — 有头手动重登（exit 2 时触发）

1. 启有头 session：
   ```bash
   camoufox-cli --session xhs-publish --persistent --headed --json open "https://creator.xiaohongshu.com/publish/publish?source=official"
   ```
2. 告知用户「**小红书创作者** 浏览器已打开，请在窗口里手动扫码登录，完成后告诉我」，**Stop and wait** 等用户确认。
3. 用户确认后导出 + 验证：
   ```bash
   xhs-publish login-verify
   ```
   脚本闭环：导出 cookie 到临时 → 创作者域 `personal_info` 裸 GET 验过才 commit → 写 `~/.openclaw/logins/xhs-publish.json` + `.ua.json` → close session。验证不过 exit 2、不重试。

> **同时导入 cookie 和 UA**：xhs 的 `a1`/`websectiga` 等设备指纹 cookie 必须配同一指纹的 UA，否则被风控错配。`publish_xhs.py` 已同时读两文件。

> 确保 `Pillow` 已安装（读图片尺寸）：`pip install Pillow`。

---

## 使用方式

通过 PATH 调用 wrapper：`xhs-publish "<正文>" [附件...]`。

### 图文笔记

```bash
xhs-publish --mode image --title "笔记标题" --body "正文内容 #话题1 #话题2" --images img1.jpg img2.jpg img3.jpg
```

### 视频笔记

```bash
xhs-publish --mode video --title "笔记标题" --body "正文内容" --video video.mp4 --cover cover.jpg
```

#### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--mode` | 是 | `image` 或 `video` |
| `--title` | 是 | 笔记标题，最多 20 字 |
| `--body` | 是 | 正文，最多 1000 字；`#话题` 自动提取为标签，**最多 10 个**（硬约束） |
| `--images` | 图文必填 | 图片路径列表，最多 18 张，jpg/png/webp |
| `--video` | 视频必填 | 视频路径，mp4，建议 9:16 |
| `--cover` | 否 | 封面图；视频模式默认取第一帧 |
| `--topics` | 否 | 额外话题名称 |
| `--private` | 否 | 仅自己可见（默认公开） |

> **⚠️ `--body` 必须传实际文字，不能传文件路径或 `$(cat file)`**：exec sandbox 禁用 `$(...)` 命令替换，`--body post.md` 也会被当字面量字符串。把正文直接硬编码进命令。

---

## 内容规范

- 标题 ≤ 20 字，正文 ≤ 1000 字
- 图片建议 3:4 竖版，最多 18 张；视频建议 9:16，5s–15min
- AI 生成内容需声明（脚本默认声明）；禁止引流、导流
- hashtag 最多 10 个（超出会被静默丢弃或限流）

---

## Agent 工作流

1. 探活：`xhs-publish check`（exit 0 = 有效；批量只探活一次）
2. 准备素材（图片/视频 + 标题 + 正文）
3. 运行 `xhs-publish ...` 发布
4. 看 stdout JSON：
   - `{"ok": true, "note_id": "xxx", "url": "https://www.xiaohongshu.com/explore/xxx"}` → 成功
   - `{"ok": false, "error": "AUTH_EXPIRED"}` → 走 Step 2 重登后重试一次
   - `{"ok": false, "error": "..."}` → 反馈用户

---

## 错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| AUTH_EXPIRED | cookie 失效 | 走 Step 2 重登后重试一次 |
| UPLOAD_FAILED | COS 上传失败 | 检查文件格式/大小，重试一次 |
| TITLE_TOO_LONG | 标题超 20 字 | 截断后重试 |
| BODY_TOO_LONG | 正文超 1000 字 | 精简后重试 |
| RATE_LIMIT | 发布频率限制 | 等 30 分钟后重试 |
