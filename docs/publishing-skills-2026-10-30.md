# 图文发布问题修复（2026-10-30）

对应本机报告：`~/.openclaw/workspace-main/issue-report/2026-10-30-publishing-skills.md`。
范围为抖音视频遗留任务对账、X 发布错误分类、公众号小绿书说明与草稿回执。

## 抖音

`video_publish.work_items` 原先要求列表内及跨页时间严格倒序，遇到旧作品即可停止扫描。
该假设与置顶、非时间排序不兼容，会触发 `WORK_LIST_ORDER_UNCONFIRMED`，留下阻塞新发布的 pending 状态。

- 自动对账遍历分页后再按提交时间、baseline、完整文案和已有作者 ID 匹配，不按首项或最新一条猜测。
- 保留分页循环、无效时间、扫描上限和同名歧义保护；无法完整自动核查时不宣称成功。
- 新增 `douyin-publish video close --outcome published --url ... --confirmation @文件 --confirm`。
  官方短链由脚本解析，无需复制 API 登录态；在本人列表中找到该确切 ID 后仍须通过原任务匹配条件。
  指定 ID 可消除同名歧义，找到目标后无需继续扫描无关旧作品。
- 新增同入口 `--outcome cancelled`，仅在用户明确授权后解除本地阻塞，不删除或撤回线上作品，不推断原提交未发布。
- 不带 `--confirm` 仅预览。两种结案均在发布排他锁内保留原始收据、用户确认、变更前后状态及应用审计。
  `edit-draft --confirm-unpublished` 的人工恢复分支也保留审计。

操作说明见 `crews/main/skills/expert-douyin/tools/douyin-publish/references/video.md`。

## X / Twitter

原外层把整个发布子进程的失败统一保存为 `unknown`，没有区分媒体上传与帖子提交。

- 在本地传输适配层观察实际请求，在可能提交帖子前记录 `submission_attempted:true`；后续错误不能清除该事实。
- 明确的 code 64 分类为 `ACCOUNT_SUSPENDED`；认证错误沿用 `AUTH_REQUIRED` / `AUTH_EXPIRED`。
- 能证明帖子提交尚未开始时，上传失败返回 `MEDIA_UPLOAD_FAILED`，收据保存为 `failed`，明确 `submission_attempted:false`。
- 帖子提交超时、帖串中途失败或进程失联且没有阶段证据时，继续保留 `PUBLISH_UNKNOWN` 和防重发保护。
- 错误输出包含 `stage`、`submission_attempted`、`failure_reason` 和脱敏上游诊断。
  既有 `unknown/submitting` 收据先拦截，不用后来观察到的上传或账号错误覆盖旧提交事实。
  `failed` 收据再次调用只返回原失败，不自动重试。

未修改上游业务或签名代码，未升级依赖。

## 小绿书

客户端完整 Markdown 会传入 Relay；本机 Relay 与 Wenyan 的图片消息分支保留正文，
跳过 HTML 排版，以 `content` 交给图片消息草稿发布函数。`description` 添加引用前缀，不覆盖正文。

- 技能补充正文、官网 CTA 和 description 的完整示例。
- 客户端成功回执末行新增 JSON：`status:draft_created`、`draft_created:true`、`published:false` 和 `media_id`。
- 缺少草稿 ID 时不宣称推送成功；`article_url` 本身不作为正式发布证据。

## 验证与生效范围

新增问题回归位于本机忽略的 `test/publishing/`：

- `test_issues_20261030.py`：置顶及无序分页、歧义、扫描边界、链接身份、预览、结案备份、会话恢复、审计失败及草稿回执。
- `x_issues_20261030.test.mjs` + `mock_x_requests.mjs`：经真实本地 X 发布入口模拟 403/code64、认证、其他 403、上传超时、提交超时、帖串及旧收据保护。全部请求拦截。
- `wx_image_content.test.mjs`：经本机 Relay 与已安装 Wenyan 实现验证正文、CTA、description 前缀；草稿发布函数替换为假实现。
  可用 `TEST_RELAY_ROOT` 指定本地 Relay 仓路径，缺省为相邻的 `wiseflow-relay`。

新增及相关既有回归共 158 项通过，三份修改后的 SKILL.md 校验通过，`git diff --check` 通过。
测试与夹具保持在仓根 `test/`，遵循现有忽略规则。

本机三个相关技能均软链到当前代码仓，新调用会读取修改；未重启 Gateway、浏览器或 Relay。
未实号发布、重发、修改既有运行收据或发布数据库，也未远端读取小绿书草稿展示。
代码提交与推送不代表已经完成实号发布验收。
