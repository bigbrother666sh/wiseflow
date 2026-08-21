# 心跳/定时任务

## 凌晨复盘任务

### 执行约束

1. **无时间限制**:任务执行不受深夜时间限制,必须执行完 HEARTBEAT 清单全部内容

2. **遇到技术故障时处理方案**:

   - **spawn IT Engineer**协助解决:调用 `sessions_spawn`,将问题现象、错误信息、当前任务上下文完整传递给 IT Engineer,请它协助解决。**spawn 后 fire-and-forget,严禁 `sessions_yield` 等待**——IT Engineer 的结果通过 announce 异步回来,若没回来按下一条跳过继续(见下方约束 3);
   - 仍无法解决 → **跳过当前任务,继续执行后续步骤**,不要卡住整个 HEARTBEAT

   不可:
      - ❌ 呼唤用户协助解决,HEARTBEAT 在深夜执行,喊用户也没用
      - ❌ 不可中断任务,通过以上三步依然无法进行的任务则跳过,继续执行后续步骤,绝对不允许中断HEARTBEAT!

3. **⛔ cron/heartbeat isolated session 中禁止 `sessions_yield`,原则上也不 spawn subagent**:

   本任务由 cron 以 `session_target=isolated` 启动,**本身已是独立上下文**,不占主 agent 上下文、不阻塞主 session。再 spawn subagent 是零收益纯增复杂度,且 `sessions_yield` 会**直接 abort 当前 run**,cron 将 yield 视为 run 结束并标记 outcome,session 变 inactive;subagent 完成后的 announce 找不到可唤醒的活跃 session,retry 3 次后 give-up,**后续 Step 全部丢失**。

   - 所有 Step 1–5 **顺序内联执行**,评估报告等产出主 agent 自己写,不 spawn subagent、不 `sessions_yield`。
   - 唯一允许 spawn 的是约束 2 的「故障兜底 spawn IT Engineer」,且必须 fire-and-forget(不 yield)。

4. **⛔ 登录失效一律「跳过 + 记录 + 汇总上报」，严禁硬行恢复登录**

   任何平台的取数端登录失效（`SESSION_EXPIRED` / 探活失败 / 浏览器跳登录页 / `get-xhs-user-id.sh` exit 2 等）时，**必须**：
   - 立即**跳过该平台**本轮取数，不再尝试任何取数动作；
   - 把平台名记入 `EXPIRED_PLATFORMS`，在 Step 5 统一汇报，由用户**白天**重新登录；
   - **不得**在凌晨心跳里扫码登录、不得唤醒用户。

   **严禁的"硬行恢复"动作**（任一都可能触发平台风控/限流/封号）：
   - ❌ 用 CDP `Network.setCookies` 把本地存的 cookie **注入**浏览器去"造"一个登录会话
   - ❌ 反复刷新/重导航 profile 页试图"刷出"登录态

   > 本规范下方 Step 2 / Step 5 已写明，但 **2026-06-29 凌晨 Agent 未遵守**：xhs-browse 浏览器无登录态时，Agent 用 CDP 注入 22 个 cookie 强造会话后批量抓取，**当日触发小红书风控、账号被处罚**。故在此特别前置强调。

5. **⚠️ 小红书 (xhs) 封号风险显著高于其他平台**

   - xhs 对「会话凭空 materialize + 短时批量签名请求」极度敏感，**一次** CDP 注入 cookie + 批量 feed 抓取就可能触发风控/限流/封号。
   - xhs-browse 任何登录失效迹象 → **立刻整段跳过 xhs**，不要尝试任何恢复，记入 `EXPIRED_PLATFORMS` 等白天重新登录。
   - 取数只走 `xhs-browse`；**禁止**探测/使用 `xhs-publish` creator 域 cookie（见 Step 2 注意事项）。

---

### 工作流程

#### Step 1: 通过 published-track 读取待取数的已发布内容

```bash
# 对每个平台，查询近期记录（取数时效窗口内，见 Step 2）
published-track query --platform xhs --limit 50
```

对每个平台列出取数时效窗口内的记录，准备在 Step 2 中更新互动数据。

---

#### Step 2: 依次获取已发布内容的互动数据并更新到 published-track

对 Step 1 中列出的**每条记录（按 id 逐条）**取数并写库。按平台分三种情况：

1. **douyin / xhs / kuaishou / bilibili** —— 走 `published-track fetch-metrics`（纯 HTTP+cookie 链路：login-manager 探活 → fetch-retro-data.ts → 写库）：

   ```bash
   published-track fetch-metrics \
     --platform <platform> --id <rowid>
   ```

   脚本封装了完整流程，返回统一 JSON 结果。**wx_mp 不走这个脚本**——机制不同，见下方第 2 条。

2. **微信公众号 (wx_mp)** -- **走 `expert-wx-mp` 包内 `wx-mp-engagement` 工具**（PATH wrapper 同名），camoufox 抓创作者中心方案，与上面四个平台的纯 HTTP+cookie 链路完全不同，两条路独立、不耦合：

   ```bash
   wx-mp-engagement fetch --row-id <rowid>
   ```

   内部流程：camoufox 打开创作者中心首页看 redirect URL 判登录态（跳 `/cgi-bin/home?token=xxx` = 就位，跳 `login`/`scanloginqrcode` = 失效）→ 从 redirect URL 提 token 拼「发表记录」页 URL → camoufox 抓发表记录页 → 解析 innerText 按标题匹配 → update-metrics.sh 写 pub_wx_mp。不导出 cookie/UA/token——登录态在 `wx_mp` session profile 里就位即可。SESSION_EXPIRED（exit 2）按通用规则跳过 + 记入 `EXPIRED_PLATFORMS`。

   > ⚠️ 不要调 `published-track fetch-metrics --platform wx_mp`——该子命令对 wx_mp 直接 exit 1 报错提示走 wx-mp-engagement。两条链路独立维护，避免机制错配。

3. **微信视频号 (wx_channel)** —— **走 `wx-channel-engagement` 技能**，camoufox 抓视频号助手后台方案，与 wx_mp 同源（camoufox + 解析 innerText）、与第 1 条四个纯 HTTP+cookie 平台机制完全不同，两条路独立、不耦合：

   ```bash
   wx-channel-engagement fetch --row-id <rowid>
   ```

   内部流程：camoufox 打开视频号助手后台首页看 redirect URL 判登录态（跳 `/platform/home` 等后台路径 = 就位，跳 `login`/扫码页 = 失效）→ 打开作品管理页（`channels.weixin.qq.com/platform/post/list`）→ 解析 wujie shadow DOM innerText 按标题匹配 → update-metrics.sh 写 pub_wx_channel。不导出 cookie/UA/token——登录态在 `wechat-channel` session profile 里就位即可。**与 `wechat-channels-publish` 共管 `wechat-channel` session**（靠 session 名字符串约定共享登录态）。SESSION_EXPIRED（exit 2）按通用规则跳过 + 记入 `EXPIRED_PLATFORMS`。

   > ⚠️ 不要调 `published-track fetch-metrics --platform wx_channel`——该子命令对 wx_channel 直接 exit 1 报错提示走 wx-channel-engagement。两条链路独立维护，避免机制错配。

**其他平台** —— 除 douyin / xhs / kuaishou / bilibili / wx_mp / wx_channel 外，其他平台暂不支持自动取数，直接跳过。

##### 取数时效窗口

**发布超过 30 天的内容不再每天抓取互动数据**——数据已稳定，边际变化可忽略，反复抓只浪费配额/增加风控暴露。按平台类型：

- **浏览器方案**（wx_mp / wx_channel）：列表页/创作者中心天然只展示近期内容，无需额外过滤——老内容不在列表里自然抓不到，**这是设计不是 bug**，不要加翻页去补抓老内容。
- **接口方案**（xhs / bilibili / douyin / kuaishou）：Step 1 查询时加 `publish_date >= date('now', '-30 days')` 过滤，超过 30 天的行直接跳过不调 `published-track fetch-metrics`。

**DNA 评估（Step 3）不受此限**

##### 通用规则

- **必须传 `--id <rowid>`**（脚本类平台）：`<rowid>` 取自 Step 1 查询结果里的 `id` 字段。同一 `source_folder` 可能对应多条记录（同内容重复发布到不同帖子），按 `--id` 逐条抓取/写库才能让每次发布各自独立统计；若只传 `--source-folder`，脚本会只抓一行指标却批量写进所有同 folder 行，造成重复发布之间互相污染。
- **SESSION_EXPIRED**：脚本返回 `ok=false, error=SESSION_EXPIRED`（exit 2）时，**跳过该平台**本轮取数，记入 `EXPIRED_PLATFORMS`，Step 5 统一汇报，由用户白天重新登录。**凌晨不唤醒用户、不扫码登录、不私拉会话**（见约束 4/5）。
- **xhs 风控显著高于其他平台**：xhs 任何登录失效迹象 → 立刻整段跳过 xhs，不尝试任何恢复。取数只走 `xhs-browse`，**禁止**探测/使用 `xhs-publish` creator 域 cookie。
- **⛔ 取数失败时必须原样报告脚本 stderr + exit code，禁止自行归因**：脚本的 stderr 是排查的唯一可靠依据。Agent 不得根据 DB 字段（如 `publish_url` 是否为空）脑补错误原因、不得改写/概括 stderr 成自己的话。例：`wx-mp-engagement fetch` exit 1 stderr=`error: 发表记录页未找到标题匹配的 row id=3`，就报这个原文，不要脑补成 "publish_url 无效"。错误归因错误会误导排查方向。

---

#### Step 3: content-calibrator DNA 表现评估（按量触发）

数据采集每天跑，但 DNA 评估**按量触发**——每个（平台, DNA）的成熟待评估记录（发布 ≥3 天 且 `perf_evaluated=0`）累积 **≥5 条**才评估一轮。先跑廉价阈值检查（各启用平台各一次）：

```bash
content-calibrator eval --platform <platform> --check
```

返回 JSON：`{dnas: [{dna_id, pending, triggered}]}`
- 全部 `triggered=false` → 本轮评估跳过，不消耗后续 token
- 有 `triggered=true` 的 DNA → 进入 Step 3a

##### Step 3a: 有专家包的平台 → 走该平台 review workflow

触发的 DNA 属于哪个平台，就按该平台专家包的 review workflow 执行完整复盘（聚合、平台归因、写报告、标记全在 workflow 内；**workflow 不取数**——本轮数据已在 Step 2 采集就位）：

- **wx_mp** → expert-wx-mp 的 Review Workflow（`skills/expert-wx-mp/workflows/review.md`）

##### Step 3b: 无专家包 review workflow 的平台 → 通用流程

按 `content-calibrator/SKILL.md` 的共性归因步骤执行：聚合 → 回读 DNA 文档与作品原文 → 写 `dna/<platform>/<dna-id>/evals/{YYYY-MM-DD}.eval.md` → 标记：

```bash
content-calibrator eval --platform <platform> --mark-evaluated --ids <本轮覆盖的记录 id，逗号分隔>
```

无平台归因方法时结论只写「观察」级。

**Step 2 取数失败时评估不跳过**：若 DB 里已有历史互动数据（reads/likes/plays 等 > 0），评估**必须用已有数据做**；只有完全没有数据（全 0）且取数也失败时才跳过。

**Agent 不得自动更新 DNA**——评估建议经 Step 5 上报，用户逐条确认后走对应平台专家包的 style-dna workflow 回写。

---

#### Step 4: 用户咨询回复

> 现阶段暂时跳过

巡检如下平台：，针对项目咨询类的留言、回复、私信进行简短回复,如:

```
项目那里下载?
怎么用?
代码仓在哪里?
支持 xxx 功能吗?
...
```

---

#### Step 5: 汇总执行情况报告用户

汇总执行情况，反馈用户。报告内容：

1. 各平台数据更新情况（成功/跳过/失败数量）
2. **取数端 Cookie 失效列表**（如有）：
   > ⚠️ 以下**取数端**Cookie 已失效，数据未能更新。请白天通知小贝重新登录：
   > - douyin（抖音）
   > - xhs-browse（小红书浏览端）
   > - wechat-channel（微信视频号)
   >
   > **只报告取数端 cookie**。**不要报告、也不要探测 `xhs-publish`（小红书发布端 / creator.xiaohongshu.com）**：
   > 复盘/取数完全不依赖发布端 cookie，探测它只会给 creator 域增加风控概率且结论与取数无关。
   > 发布端失效由发布任务（xhs-publish 技能）自己管，不在本复盘心跳职责内。
3. DNA 表现评估摘要（如有）：列出本轮评估的 DNA（平台 / dna-id / 覆盖篇数）+ 整体判定（改善 / 平稳 / 下滑）+ 关键归因；无触发 DNA 时写「无 DNA 达到评估阈值」并附各 DNA 待评估计数。
4. **DNA 优化建议待确认（如有）**：列出评估报告中的逐条建议（建议内容 + 目标维度/template 部分 + 证据篇目）。**Agent 不得自动更新 DNA**。用户白天逐条确认后，指示走对应平台专家包的 style-dna workflow 回写 DNA。
5. 用户咨询回复摘要。

发送后本次定时任务结束。
