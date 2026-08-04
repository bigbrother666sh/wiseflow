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

   - 所有 Step 1–5 **顺序内联执行**,retro.md 等产出主 agent 自己写,不 spawn subagent、不 `sessions_yield`。
   - 唯一允许 spawn 的是约束 2 的「故障兜底 spawn IT Engineer」,且必须 fire-and-forget(不 yield)。

4. **⛔ 登录失效一律「跳过 + 记录 + 汇总上报」，严禁硬行恢复登录**

   任何平台的取数端登录失效（`SESSION_EXPIRED` / 探活失败 / 浏览器跳登录页 / `get-xhs-user-id.sh` exit 2 等）时，**必须**：
   - 立即**跳过该平台**本轮取数，不再尝试任何取数动作；
   - 把平台名记入 `EXPIRED_PLATFORMS`，在 Step 5 统一汇报，由用户**白天**用 login-manager 重新登录；
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

#### Step 1: 通过 published-track 读取所有已启用打分（cal_enabled=1）的已发布内容

```bash
# 查看哪些平台启用了 content-calibrator
./skills/content-calibrator/scripts/cal-toggle.sh --list

# 对每个已启用平台，查询有 cal_enabled=1 的记录
./skills/published-track/scripts/query.sh --platform xhs --limit 50
```

对每个已启用平台，列出所有 `cal_enabled=1` 的记录，准备在 Step 2 中更新数据。

---

#### Step 2: 依次获取已发布内容的互动数据并更新到 published-track

对 Step 1 中列出的**每条记录（按 id 逐条）**取数并写库。按平台分三种情况：

1. **douyin / xhs / kuaishou / bilibili** —— 走 `fetch-and-update-metrics.sh`（纯 HTTP+cookie 链路：login-manager 探活 → fetch-retro-data.ts → update-metrics.sh）：

   ```bash
   ./skills/published-track/scripts/fetch-and-update-metrics.sh \
     --platform <platform> --id <rowid>
   ```

   脚本封装了完整流程，返回统一 JSON 结果。**wx_mp 不走这个脚本**——机制不同，见下方第 2 条。

2. **微信公众号 (wx_mp)** —— **走 `wx-mp-engagement` 技能**，camoufox 抓创作者中心方案，与上面四个平台的纯 HTTP+cookie 链路完全不同，两条路独立、不耦合：

   ```bash
   wx-mp-engagement fetch --row-id <rowid>
   ```

   内部流程：camoufox 打开创作者中心首页看 redirect URL 判登录态（跳 `/cgi-bin/home?token=xxx` = 就位，跳 `login`/`scanloginqrcode` = 失效）→ 从 redirect URL 提 token 拼「发表记录」页 URL → camoufox 抓发表记录页 → 解析 innerText 按标题匹配 → update-metrics.sh 写 pub_wx_mp。不导出 cookie/UA/token——登录态在 `wx_mp` session profile 里就位即可。SESSION_EXPIRED（exit 2）按通用规则跳过 + 记入 `EXPIRED_PLATFORMS`。

   > ⚠️ 不要调 `fetch-and-update-metrics.sh --platform wx_mp`——该脚本对 wx_mp 直接 exit 1 报错提示走 wx-mp-engagement。两条链路独立维护，避免机制错配。

3. **其他平台** —— 使用平台对应的持久化 session 通过 `camoufox-cli` 打开平台创作者中心，读取已发布文章的互动数据再写库。

   > 这条路效果一般，**尽力而为即可，不要硬弄**——拿不到就跳过，切勿反复操作以免引发风控。后面会持续更新。

##### 取数时效窗口

**发布超过 30 天的内容不再每天抓取互动数据**——数据已稳定，边际变化可忽略，反复抓只浪费配额/增加风控暴露。按平台类型：

- **浏览器方案**（wx_mp 等）：列表页/创作者中心天然只展示近期内容（wx_mp 发表记录页 `count=20`），无需额外过滤——老内容不在列表里自然抓不到，**这是设计不是 bug**，不要加翻页去补抓老内容。
- **接口方案**（xhs / bilibili / douyin / kuaishou）：Step 1 查询时加 `publish_date >= date('now', '-30 days')` 过滤，超过 30 天的行直接跳过不调 `fetch-and-update-metrics.sh`。

**复盘（Step 3）不受此限**——复盘按 T+3d 窗口 + 有 `prediction.md` 无 `retro.md` 判断，可能涉及发布较早但尚未复盘的内容。Step 2 没抓到新数据时，复盘用 DB 里已有的历史数据。

##### 通用规则

- **必须传 `--id <rowid>`**（脚本类平台）：`<rowid>` 取自 Step 1 查询结果里的 `id` 字段。同一 `source_folder` 可能对应多条记录（同内容重复发布到不同帖子），按 `--id` 逐条抓取/写库才能让每次发布各自独立统计；若只传 `--source-folder`，脚本会只抓一行指标却批量写进所有同 folder 行，造成重复发布之间互相污染。
- **SESSION_EXPIRED**：脚本返回 `ok=false, error=SESSION_EXPIRED`（exit 2）时，**跳过该平台**本轮取数，记入 `EXPIRED_PLATFORMS`，Step 5 统一汇报，由用户白天用 login-manager 重新登录。**凌晨不唤醒用户、不扫码登录、不私拉会话**（见约束 4/5）。
- **xhs 风控显著高于其他平台**：xhs 任何登录失效迹象 → 立刻整段跳过 xhs，不尝试任何恢复。取数只走 `xhs-browse`，**禁止**探测/使用 `xhs-publish` creator 域 cookie。
- **⛔ 取数失败时必须原样报告脚本 stderr + exit code，禁止自行归因**：脚本的 stderr 是排查的唯一可靠依据。Agent 不得根据 DB 字段（如 `publish_url` 是否为空）脑补错误原因、不得改写/概括 stderr 成自己的话。例：`wx-mp-engagement fetch` exit 1 stderr=`error: 发表记录页未找到标题匹配的 row id=3`，就报这个原文，不要脑补成 "publish_url 无效"。错误归因错误会误导排查方向。

---

#### Step 3: content-calibrator 复盘

一键扫描待复盘作品 + 带出互动数据（有 `prediction.md` 无 `retro.md` + 过 T+3d 窗口的 `cal_enabled=1` 记录）：

```bash
./skills/published-track/scripts/query-retro-pending.sh --days 3 --min-count 5
```

返回 JSON：`{total, min_count, pending: [{source_folder, title, prediction_path, publish_date, cal_scores, platforms: {<platform>: {id, metrics}}}]}`
- `total < min_count` → 待复盘积攒不够，跳过本轮复盘
- `total >= min_count` → 对 `pending` 数组里每个作品执行复盘流程

复盘流程（由 Agent 执行，每个作品一份）：
- 读 `prediction_path` 拿预测（路径已在 JSON 里，无需自己拼）
- 对比预测 vs `platforms` 里各平台的实际 `metrics`（数据已在 JSON 里，无需再查 DB）
- 写 `<source_folder>/calibration/retro.md`（T+3d 写一次，immutable，含多平台实绩对比）
- 提炼观察 → 写入**统一** `calibration/rubric-memo.md`（根级，非平台目录；见 content-calibrator SKILL.md 归集表）
- 检测是否触发 bump（≥3 次同向偏差）

**Step 2 取数失败时复盘不跳过**：若某条记录 Step 2 取数失败但 DB 里已有历史互动数据（reads/likes/plays 等 > 0），复盘**必须用已有数据做**，不得因 re-fetch 失败就跳过复盘。只有 DB 里完全没有数据（全 0）且取数也失败时才跳过。

**如果某平台未启用 content-calibrator，跳过此步骤。Agent 不得自动启用。**

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
   > ⚠️ 以下**取数端**Cookie 已失效，数据未能更新。请白天使用 login-manager 技能重新登录：
   > - douyin（抖音）
   > - xhs-browse（小红书浏览端）
   >
   > 列出的名字即 `login-manager login <name>` 要用的平台名（非 published-track 的 `xhs`）。
   >
   > **只报告取数端 cookie**。**不要报告、也不要探测 `xhs-publish`（小红书发布端 / creator.xiaohongshu.com）**：
   > 复盘/取数完全不依赖发布端 cookie，探测它只会给 creator 域增加风控概率且结论与取数无关。
   > 发布端失效由发布任务（xhs-publish 技能）自己管，不在本复盘心跳职责内。
3. content-calibrator 复盘结果摘要（如有）：列出本轮复盘的**每个作品**（`source_folder` / 标题）+ 预测 vs 实际对比简述 + 是否触发 bump 信号
4. 用户咨询回复摘要。

发送后本次定时任务结束。
