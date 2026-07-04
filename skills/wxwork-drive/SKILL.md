---
name: wxwork-drive
description: Upload images and videos to WeChat Work WeDrive (企业微信微盘). Supports local
  mode (IP whitelisted) and relay mode via tx-relay proxy. Handles chunked upload
  for large videos automatically.
metadata:
  openclaw:
    emoji: 💾
    requires:
      bins:
      - curl
      - python3
---

# WeChat Work WeDrive Upload（企业微信微盘上传）

将图片或视频上传到企业微信微盘（WeDrive）。

> 📍 **全局技能路径提示**：文中所有 `./scripts/` 路径均相对于本技能所在目录（即 `<skill>` 标签 `location` 属性所指目录），**不是**工作区目录。执行时按本技能实际安装路径拼接。

---

## 上传命令

```bash
python3 {skillDir}/scripts/upload-drive.py <file_path> <spaceid> <fatherid>
```

- `file_path`：本地文件路径（jpg/png/gif → 图片；mp4/mov/avi/wmv → 视频）
- `spaceid`：微盘空间 ID（可在微盘 Web 端 URL 中找到）
- `fatherid`：目标文件夹 ID（根目录时填入 `spaceid` 本身）

脚本自动处理：
- 模式判断（local vs relay）
- 图片：直接上传
- 视频（relay）：单次请求，服务端分块
- 视频（local）：本机分块 → SHA1 校验 → 三步完成（需 `pip install requests`）

---

## 返回值

```json
{ "ok": true, "fileid": "3a8YSzXXXXXXXX", "fast_forward": false }
```

`fast_forward: true` 表示命中秒传，文件已存在于微盘。

---

## Agent 行为约束

1. 视频上传可能耗时较长（100MB 约 1–3 分钟），**等待脚本完整返回后**再进行下一步，期间告知用户"正在上传..."
2. **禁止**手动拼接 curl 命令替代脚本

---

## Error Handling

| 错误 | 原因 | 处理 |
|------|------|------|
| `请配置环境变量` | 两组变量均未配置 | 配置对应环境变量 |
| `invalid ip` | 本机 IP 未加入企业微信可信 IP | 后台添加 IP；或改用 relay 模式 |
| `401 Unauthorized` | relay 模式 api_key 错误 | 检查 `WENYAN_API_KEY` |
| `no privilege` | 应用未开通微盘权限 | 企业微信后台开通权限 |

---

## Notes

- `fileid` 永久有效（文件未被删除），可长期引用
- 本地直连视频上传需额外安装：`pip install requests`
