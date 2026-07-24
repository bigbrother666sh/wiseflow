# Step 2 — 脚本创作与定稿（stages/ 子文档）

> 主 SKILL.md 在此段只保留导航指针，subagent 跑到 Step 2 时才主动 read 此文。

脚本必须包含**片段拆分规划**——每个片段对应一次 `gen.py` 调用或一个用户素材，时长不超过模型限制。

#### 2.1a 正常流程（文章/文字主题）

按「开篇抓眼球 → 中段讲卖点 → 结尾促下单」三段式结构撰写脚本。

**三段式结构**：

| 段落 | 时长占比 | 目标 | 示例套路 |
|------|---------|------|---------|
| **开篇抓眼球** | 前 15–20% | 3 秒内让人停止划走 | "99% 的人都不知道…" / "我花了 XX 才搞明白" / 强反差开场 |
| **中段讲卖点** | 60–70% | 展示核心价值，每个卖点一句 | 场景化痛点 → 产品/方法解决 → 数据/案例佐证 |
| **结尾促下单** | 后 15–20% | 明确 CTA，降低决策门槛 | "链接在简介" / "点击立即领取" / "限时优惠只剩 XX 件" |

#### 2.1b 作为 viral-chaser 技能的后续步骤

读取 `raw_article.md`（追爆报告），按报告中的内容结构、爆款元素和可借鉴点生成脚本。**不套用三段式结构**，而是按照追爆报告拆解的原视频结构来组织脚本，保留叙事节奏和钩子类型。

#### 2.2 片段拆分（脚本必含项）

##### 2.2.1 项目音色设定

声画同出模式下，模型按 prompt 中的音色描述生成人声，没有 voice ID 可传。**同一项目内旁白音色、同一角色音色必须跨片段一致**，否则成片声音段间跳变。脚本必须在片段规划表之前定义一份项目级音色设定，每段旁白逐字复用：

```markdown
## 项目音色设定

- 旁白音色：<具体到性别/年龄感/音色质感/语速/语气，如"沉稳男声，30岁左右，略带磁性，语速适中偏慢，叙述感强">
- 角色音色（人物故事模式按角色列，非人物故事可省）：
  - 主角（character_reference.jpg）：<如"年轻女性，温柔清亮，语速偏快，口语化">
  - 配角：<…>
```

上述音色设定是跨片段整个脚本通用的设定，要放置在 `script.md` 中 `## 片段规划` 前面，并最后随片段规划一起发用户确认。

**音色一致性规则（强制）**：
- 音色描述要具体，不得只写"男声/女声"
- **音色描述只在「项目音色设定」里写一次，片段规划表里不重复**——片段规划的「音频描述」列只写旁白文案/BGM/环境音，不写音色
- **调用 `gen.py` 时，必须把本段对应的音色描述逐字拼进 `--prompt`**（旁白段拼旁白音色，人物对话段拼对应角色音色），逐字复用、不得改写、换词、增删修饰——这是声画同出下成片声音统一的唯一保证
- 同一角色跨段必须用同一条音色描述；换角色才换描述
- ⚠️ 声画同出模型（wan2.7 / happyhorse / 火山 Seedance）均**无音色 ID 或参考音锁定能力**，`--ref-audio` 实测三平台都不认。音色一致**只能靠每段 prompt 逐字复用同一条音色描述**来近似保持——这是目前唯一手段，定稿时务必把音色描述钉死、段间一字不改

##### 2.2.2 片段规划

```markdown
## 片段规划

| # | 段落 | 画面描述 | 音频描述 | 时长 | 来源 |
|---|------|---------|---------|------|------|
| 01 | 开篇 | 产品特写，科技感背景，光影流转 | 旁白："99%的人都不知道…" + 悬念BGM起 + 无 | 5s | AI生成 |
| 02 | 中段 | 用户使用场景，手机操作画面 | 旁白："只需要三步…" + BGM + 键盘敲击声 | 8s | AI生成 |
| 03 | 中段 | 数据图表动画，对比效果 | 旁白："效率提升300%" + BGM + 无 | 6s | AI生成 |
| 04 | 结尾 | 产品logo+CTA按钮 | 旁白："立即体验" + BGM收尾 + 无 | 5s | AI生成 |
```

**拆分规则**：
- 每个片段时长 ≤ 15 秒
- 如果用户提供了素材，在「来源」列标注为 `用户素材`，并注明素材文件名
- **每个 AI 生成片段的「音频描述」必须写明三层**（声画同出，gen.py 照此生成声音，定稿时用户确认的就是成片实际听到的）：
  - **旁白解说**：`旁白："具体文案"`，文案是要朗读的整句（不是"说一段开场白"这种泛指），这就是成片台词，用户定稿即确认
  - **背景音乐**：风格/情绪/起止（如"温暖钢琴 BGM 全段铺底，结尾渐弱"）；同一项目 BGM 风格也应统一，跨段复用同一 BGM 描述
  - **环境音/音效**：关键音效（如"键盘敲击声""金币叮声"），无则写"无"
- 画面描述同样要足够详细（人物/场景/动作/镜头运动）
- 编号 `01, 02, 03…` 对应最终 artifacts 中的文件名前缀

##### 2.2.3 slideshow-risk 自检清单（borrowed from OpenMontage storyboard gate，定稿前必跑）

**片段规划写完后、发给用户定稿前，对规划表做一遍 slideshow-risk 自检**——AI 视频生成最容易出的硬伤不是画质差，是"看起来像 PPT 翻页动画"。把这一类硬伤拦在烧视频 API 费之前。

逐段对照规划表，过 3 维清单：

| 维度 | 症状 | 检测规则 | 命中后处置 |
|------|------|---------|-----------|
| **repetition** | 多段画面描述高度雷同（同一静物特写 / 同一空镜 / 同一人物站姿） | 任两段画面描述的核心实体（人/物/场景）token 重合 ≥ 70% 即命中 | 重写其中一段换叙事功能（如把"产品正面特写"换成"用户手持产品实操"），或合并雷同段 |
| **weak-motion** | 段画面描述只有静态构图、没写镜头运动或主体动作（"手机立在桌面" / "logo 出现"） | 画面描述里没出现 `推/拉/摇/移/升/降/旋转/zoom/pan/动作动词` 任一即命中 | 给该段补镜头运动（如"镜头缓慢推近至屏幕中心"）或主体动作（如"手指滑过屏幕触发动画"）；补不出则换段 |
| **typography-overreliance** | 段画面靠字幕/文字承担信息传递（"画面出现'限时优惠'四个字" / "屏幕显示价格"） | 画面描述里文字承担信息传递、且旁白不覆盖同信息即命中 | 把该信息改由旁白口播承担；画面文字仅作辅助强调，不能独立承担信息 |

**执行约束**：
- 命中任一维度 → 重写该段画面描述，**不准发含硬伤的规划表给用户定稿**
- 命中 ≤ 1 段 → 当场改完即过；命中 ≥ 2 段 → 整体重审叙事结构，可能要回 2.1 重拆分段
- Gate 0 contact sheet 是这一关的二次兜底——关键帧静图能再拦 repetition 和 weak-motion（同构图静图会显眼）；typography-overreliance 只在脚本规划这关拦，静图拦不住
- viral-chaser 后续流程因追爆报告已含原视频分镜，repetition / weak-motion 命中率天然低，但仍要过一遍

#### 2.3 与用户确认脚本（定稿流程）

完成脚本创作后，必须将脚本原文发送给用户（直接发内容文字，不发文件或路径）。如果用户有意见，按用户意见修改，直到用户确认。

用户确认后，把定稿的脚本存入 `script.md`，进入下一步。

#### 2.3.5 Gate 0 — 关键帧 contact sheet 确认（借鉴 gbro Gate 2 + OpenMontage storyboard，定稿后、生产前）

**脚本定稿后、进入打分和生产前，强制走 Gate 0**——用 `siliconflow-img-gen` 出每段关键帧静图，合成 contact sheet 发用户全段确认，**改文字免费、重生一张图远比重跑一段视频便宜**（gbro README 原话）。这是替代上一轮"裸 gen.py 串行生成 + 逐段肉眼确认"的脆弱闸门——把隐喻/构图错误拦在烧视频 API 费之前。

**Gate 0 流程**：

1. **逐段生成关键帧静图**——对片段规划表里每段「画面描述」转成英文 prompt，调 `siliconflow-img-gen`：
   ```bash
   siliconflow-img-gen --prompt "<片段 01 画面描述英文版>" --image-size 1600x2848 --out-dir <project-dir>/keyframes/
   # 默认 doubao-seedream-4.5（不可用时脚本自动 fallback doubao-seedream-5.0-lite）
   ```
   - 输出文件名按段编号：`01_<topic-en-slug>.jpg`、`02_<topic-en-slug>.jpg` …
   - **人物故事模式（A.1）**：先用 `siliconflow-img-gen` 生人物定妆照（已有 Step 4 模式 A.1 流程），关键帧 prompt 里写 "the same character from the reference image — keep face/hair/age/outfit EXACTLY identical"，靠 siliconflow-img-gen 的 image-edit 模式（`--image character_reference.jpg`）保持一致——**不要在 Gate 0 阶段另生新人物**
   - **氛围段（A.2 t2v）**：直接生静图，无参考图
   - **用户参考图段（A.3 r2v）**：用 image-edit 模式 `--image <用户参考图>` 生静图，构图贴近未来 gen.py 会出的视频
   - ⚠️ 这一步**只生静图不调 gen.py**——目的是用图片确认构图，不烧视频 API 费

2. **合成 contact sheet**——把所有关键帧拼一张总图发用户：
   ```bash
   # 拼接策略：按段编号横向排列，每张缩到 270x480（保持 9:16 比例），最多 5 张一行多行
   ffmpeg -y -pattern_type glob -i "<project-dir>/keyframes/*.jpg" \
     -vf "scale=270:480,tile=5x1" \
     -frames:v 1 <project-dir>/keyframes/contact-sheet.jpg
   ```
   - 段数 > 5 时分多行（`tile=5x2`、`5x3`…），段数 ≤ 5 时单行
   - **把 contact-sheet.jpg 文件本体直接发到聊天里**，请用户标"哪段通过 / 哪段改 / 哪段重做"

3. **批量部分通过**——只有用户标"通过"的段才进 gen.py 批量队列：
   - 通过段 → 进 Step 4 视频素材生产
   - 要改的段 → 改 prompt 后重生该段关键帧，重新拼 contact sheet 让用户确认（递增 `contact-sheet-v2.jpg`、`v3.jpg`，不覆盖旧版便于对比）
   - 全段通过 → 进 2.4 打分流程

4. **Gate 0 旁路条件**（只在以下情况跳过）：
   - `AWK_API_KEY` 未配（siliconflow-img-gen 不可用）→ 向用户报告"Gate 0 不可用，直奔 gen.py 逐段生成 + 逐段确认"，等用户决策
   - 片段数 ≤ 2 且用户明确说"直接生视频"→ 跳 Gate 0，但 Step 4 仍走逐段确认
   - viral-chaser 后续流程且追爆报告里已含关键帧分镜描述 → 用户已在追爆阶段确认过构图，跳 Gate 0

Gate 0 产物落 `<project-dir>/keyframes/`——**不进 artifacts/、不进 previews/**，与 review.py 的 `review/` 子目录同级，互不混淆。**关键帧静图不参与最终合成**，assemble.py 只扫 `artifacts/`。

#### 2.4 脚本定稿打分+盲预测（content-calibrator）

脚本定稿后、进入生产前，对 `script.md` 做**一次盲打分 + 盲预测**并落盘到 `output_videos/<topic-en-slug>/calibration/`（视频成片后不再打分，打分锚在定稿）。**per-work：一个视频一次打分+预测**，rubric 全平台统一，各平台差异体现在预测的 bucket 上。

前置：目标视频平台中至少有一个已启用 calibration（`calibration/<platform>/.platform-state.json` 存在）。无任何已启用平台 → 跳过本步。

1. 主 agent `sessions_spawn` blind sub-agent（一定要 spawn 第二个 subagent，避免同一个 subagent 自创自评），只喂 `script.md` + `calibration/rubric_notes.md`（统一 rubric），一次输出：
   ⚠️ **spawn 时 prompt 必须强制要求**："你最后一步的 reply 正文里**必须**包含一个 JSON 代码块（装着 7 维分 + 预测）；不要只 tool-call 后 stop，不要只用 thinking 代替最终文本输出。" 不照此要求会导致某些模型路由下（如 awk/glm-latest）提前 stop 不输出文本，主 agent 拿不到结果。
   - 7 维分 ER/HP/SR/QL/NA/AB/PV（0-5）+ per-dim confidence
   - 盲预测草稿：cold-start 期一句话 bet；过 cold-start 则含每个目标平台的 bucket/中枢（各平台 baseline 不同）
2. 调 `score-only.sh --content-path <script.md> --cal-er ? …` 判阈值门（**全局阈值**，一次判定；`--platform` 可选）。
3. 调 `commit-prediction.sh --work-dir output_videos/<topic-en-slug> --platform <主平台> --cal-er ? … --prediction-file <预测草稿>` 把 `score.json` + `prediction.md` 落盘到 `output_videos/<topic-en-slug>/calibration/`（同 work 重打覆盖）。**score.json 即权威记录，不再往 `script.md` 写分数区段。**
4. `passed=false` → 向用户报告 `failing_dims`，由用户决定是否改脚本重打（最多 2 轮，重打覆盖 `score.json`+`prediction.md`）；用户不改则保留分数继续。

详见 `content-calibrator/SKILL.md` 流程 1A。发布时 `record.sh --source-folder output_videos/<name>` 自动从 `calibration/score.json` 读分；本步未落盘则 record.sh 报错（或显式 `--no-cal` 跳过）。

#### 2.5 预算估算（borrowed from OpenMontage budget gate，定稿后、生产前强制）

**脚本规划定稿 + Gate 0 通过 + 2.4 打分通过后，进入生产前强制输出全片预算估算**——用户确认估算再开跑，不准"边跑边发现贵"。这是替代上一轮"裸 gen.py 串行烧 API 费"的脆弱闸门。

**估算时机**：Gate 0 contact sheet 全段通过 + 2.4 打分 passed 之后，Step 4 开跑之前。Gate 0 旁路或 2.4 跳过的情况按各自规则处理，预算估算**不可旁路**（除非用户主动说"跳预算直接生"）。

**估算内容**（发给用户一份，落盘 `<project-dir>/budget.json` 一份）：

```json
{
  "topic": "<topic-en-slug>",
  "total_duration_s": 28,
  "segment_count": 4,
  "segments": [
    {"id": "01", "duration_s": 5, "mode": "r2v", "model": "happyhorse-1.1-r2v", "platform": "dashscope"},
    {"id": "02", "duration_s": 8, "mode": "t2v", "model": "happyhorse-1.1-t2v", "platform": "dashscope"},
    {"id": "03", "duration_s": 6, "mode": "t2v", "model": "happyhorse-1.1-t2v", "platform": "dashscope"},
    {"id": "04", "duration_s": 5, "mode": "r2v", "model": "happyhorse-1.1-r2v", "platform": "dashscope"}
  ],
  "gate0_img_calls": 4,
  "cover_img_calls": 1,
  "video_calls": 4,
  "expected_wall_minutes": 8,
  "expected_cost_cny": 0.56,
  "notes": "百炼 happyhorse-1.1 折扣价约 0.04 元/秒；火山 Seedance Fast 0.05 元/秒"
}
```

**估算算法**（agent 手工套表，不必上脚本）：
1. **API 调用次数**：
   - Gate 0 已跑过的关键帧静图调用 = 段数（`gate0_img_calls`，已花过，记入但不重算）
   - 视频生成调用 = 段数（每段一次 `gen.py`，含候选链 fallback 时的重试预估——每段加 1 次兜底重试预算）
   - 封面静图 = 1 次（`cover_img_calls`）
2. **预估耗时**：百炼单段 3–15s 视频实际渲染 1–4 分钟（happyhorse-1.1 较快，wan2.7 慢）；火山 Seedance Fast 约 30–60s/段。串行生产总耗时 = Σ段预估。加 ±30% 缓冲报给用户。
3. **预估费用**：按当前已配平台的价目套——
   - 百炼 happyhorse-1.1：约 0.04 元/秒（折扣期，按官方价目；价目变动以阿里云控制台为准）
   - 百炼 wan2.7：约 0.05 元/秒
   - 火山 Seedance Fast：约 0.05 元/秒；Normal 约 0.08 元/秒；Mini 约 0.03 元/秒
   - 硅基 siliconflow-img-gen（Gate 0 + 封面）：约 0.01–0.02 元/张
   - 候选链 fallback 预估：每段加 1 次兜底重试预算（实际多数不触发，估算法照估）
   - **价目以官方控制台为准，估算时标注"参考价，实际以账单为准"**

**用户确认协议**：
- 估算输出后**等用户明确回复"开跑"/"确认"/"继续"**才进 Step 4——不准擅自开跑
- 用户回复"太贵/耗时太长"→ 重审脚本：缩段数 / 缩时长 / 换更便宜模型（如 Seedance Mini）/ 多用 Stock Footage 替段，重出估算
- 用户回复"跳预算直接生"→ 落 `budget.json` 标 `skipped=true` + 用户原话 notes，直奔 Step 4

**逐段累计**（生产期对照，落 `<project-dir>/budget.json` 的 `actual` 字段，append-only）：
- 每段 `gen.py` 跑完记 `actual.segments[i].wall_s`（实际墙钟秒）+ `actual.segments[i].cost_cny`（按平台价目套实际时长）
- 候选链 fallback 触发时记 `actual.segments[i].fallback_to` + 追加费用（decisions.log 也会落，此处只算钱）
- **超估算 ±20% 时向用户报告**："段 NN 实际耗时/费用超估算 X%，是否继续"——不准擅自继续
- 全片完工后比对 `expected` vs `actual`，落 `budget.variance_pct` 给后续 calibration 喂数（OpenMontage 没有，是我们加的——帮 calibrator 校准未来项目的预测准度）

**budget.json 与 decisions.log 的分工**：
- `decisions.log`：append-only 决策审计，gen.py fallback 每次落一条，手不准编辑
- `budget.json`：point-in-time 预算 + 实际累计，每段更新时整体重写（不是 append），最后留 variance 供 calibrator
- 两份不同别混——`decisions.log` 记"为什么 fallback"，`budget.json` 记"花了多少时间/钱"
