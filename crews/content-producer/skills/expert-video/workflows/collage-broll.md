# Workflow：Collage B-roll（纸拼贴组装动画）

Brief 里写 `workflow: collage-broll`，或甲方要"把这句口播做成拼贴 B-roll""纸拼贴动画""半调拼贴"时使用。本文指导**从 Brief 生产纸拼贴 B-roll 的 script**（隐喻清单）及这一步之后的自检（隐喻自检，GATE A 质检标准），并附该类型的制作约定（方法论移植自 gbro-collage-broll：半调纸拼贴 + assemble-from-empty）；闸门收敛为 GATE A / GATE B 两道——**GATE A 检隐喻清单（即本类型的 script），GATE B 检静帧 contact sheet（即素材）**。不替代通用流程；原子能力、护栏、工作区与交付约定照 `expert-video` 的 SKILL.md 执行；本文与通用流程冲突处以本文为准，但闸门与护栏不让步。

## 类型定义

把一句约 5 秒的口播文稿压成一个 sharp visual idea，做成高级编辑风**半调纸拼贴（halftone paper-collage）组装动画** B-roll：

- 强烈、平坦、均匀的纯色纸面色场 + 黑白 halftone 照片剪贴为骨架 + 彩色卡纸点缀服务信息层级
- 动作是 assemble-from-empty：元素从空场逐件滑入、卡位、组装（stop-motion 质感），不是轻微漂移、晃动或慢 zoom
- 默认交付 9:16、5 秒、720×1280、无声 MP4，可直接垫在口播下面

逐条文稿 → 逐条隐喻 → 逐条独立成片。批量隐喻优先形成前后叙事（例如先表现手工消耗与经验流失，再表现规范沉淀与人机分工）。

## 输入契约（Brief 侧）

| Brief 字段 | 要求 |
|-----------|------|
| 文稿 | 甲方交付：口播形态给 `voiceover.md`（绝对路径），其余给 Brief 内文稿字段，逐条可独立成句。**落稿锁定不重写**——隐喻是文稿的视觉转译，不是改写；发现文稿无法转译（一句话塞多个隐喻、超时长带）报 Brief owner |
| form | 画幅 / 时长 / 分辨率 / 声音；未指定按默认（9:16、5s、720P、无声） |
| gates | GATE A / GATE B 批准人；代理批准时写明批准范围 |
| acceptance | 验收标准（未指定按「交付」节默认） |

## 阶段裁剪表（相对通用制作流程）

| Stage | 处置 | 本文对应 |
|-------|------|---------|
| 0 Brief intake | 照走 | 核对文稿逐条可拆、规格齐；缺字段向 Brief owner 澄清 |
| 1 script-write | **重定义** | Phase 1 隐喻设计——产物落 `script/script.md`（隐喻清单），就是本类型的"分场剧本" |
| 2 script-self-eval | **重定义** | 隐喻自检（见 Phase 1），任一条不过必返工 |
| 3–5 storyboard / shot-decompose / character-register | **裁剪** | 单镜固定机位、无人物角色，不建 storyboard / shot_decompose / characters |
| GATE A | 照走 | 呈交隐喻清单 |
| 6–9 slot-plan → delivery-promise-lock | **由纸片素材与构图替代** | Phase 2：独立素材层 + HTML/GSAP 组装 + 静帧 QA；AIGC 素材留 prompt、模型与时间 |
| GATE B | 照走 | 呈交预览 contact sheet、最终定格帧与素材来源 |
| 10 render-shot | **重定义** | Phase 3：`video-producer visual-render` 调 HyperFrames 确定性渲染；特殊生成式镜头才选 `batch-i2v` |
| 11 mix-audio | **裁剪** | 默认无声交付；甲方要声音时走公共音轨链 |
| 12 assemble | **裁剪** | 逐条独立成片，不拼接 |
| 13a video-review | 照走（强制） | 无声版 `audio_absent` warning 是预期，放行；带声版出 `audio_absent` 是 critical |
| 13b motion-audit | 照走 | 抽查组装过程逐件进入而非整体淡入 |
| 13c normalize | 无声片豁免 | 带声版必跑 |
| 14a make-cover | 按需 | B-roll 垫片通常无封面，Brief 要求才做 |
| 15 交付 | 照走 | 回报产物绝对路径 |

## Phase 1 隐喻设计（Stage 1 重定义）

先把每条文稿压成一个视觉命题，提取：

- **核心意思**：观众最终要看懂什么
- **情绪**：冷静、惊讶、紧迫、豁然开朗、荒诞、反讽
- **动作动词**：打开、连接、漏掉、装订、归档、点亮、压缩、分叉、组装
- **可视化隐喻**：机器、时钟、胶片、档案柜、控制台、规则册、漏斗、轨道、棋子

**不要把文稿逐字放进画面。** 默认一条文稿只做一个隐喻，控制在 3–6 个关键物件；元素过多语意变弱，i2v 组装也不稳定。

`script/script.md` 每条格式：

```text
1. 核心意思：经验每次都在重复消耗
   视觉隐喻：熟练剪辑师围着巨大的胶片时钟逐帧裁切，时钟走完一圈却只得到一小段成片
   关键物件：胶片时钟、剪辑师、剪刀、短胶片
   色彩：焦橙底，奶油白与浅青点色
   组装顺序：时钟 → 人物与剪刀 → 胶片 → 最终短输出
```

### 隐喻自检（Stage 2 重定义，任一条不过必返工）

1. 一句话只表达一个清晰隐喻？
2. 关键物件 3–6 个，不是满屏碎片？
3. 文稿没有逐字进画面（无字幕、无口播全文）？
4. 底色与点色按语义色场表选，有理由（见 Phase 2 色彩规则）？
5. 批量时前后叙事成立，或每条独立成立？

## GATE A：呈交隐喻清单

文本闸门——**停，结束本轮回复**，发 Brief owner 审：

- 呈交：条数、每条一句话视觉命题、色彩方案、组装顺序概览
- 甲方只确认部分编号时，只让通过的条目进 Phase 2；未通过条目改隐喻重审
- 甲方已在 Brief 代理批准时，把批准范围落 `gates/gate-a.md` 后继续

## Phase 2 纸片素材与可控组装（GATE A 批准后）

每条隐喻准备 3–6 个**独立的本地素材层**，用一张纯色 CSS 背景承载。素材可以是黑白半调人物/物件图片、彩色卡纸块、纸纹或连接件；不要求透明 PNG，规则矩形剪贴和 CSS `clip-path` 就能形成纸片。需要图像时调公共 `awk-img-gen` 分别生成，不生成一张无法拆开的完整尾帧。记录每个素材的 prompt、模型、时间和授权来源。文字、logo、水印、UI 不得混进素材。

底色按隐喻语义选择，同一批保持相近纸张质感和点色层级：焦橙/红用于时间与劳动，芥末黄用于警示与流失，墨绿用于认知与重置，深紫用于规范与沉淀，青绿用于协作与执行。主体以黑白半调为主，彩色卡纸只标出信息重点。

`script/visual-spec.json` 逐条记下 `script_meaning`、`visual_metaphor`、`style_signature`、`color_field.background_hex`、`elements`（各含 `what`、`role`、`asset`、`placement`、`enter_at`）、`composition.final_frame` 和 `motion_plan`。素材提示词写进 `script/imagegen-prompts.md`；对每个物件分别请求一致的半调纸拼贴质感和干净剪贴边缘，并禁文字、数字、logo、水印和 UI。

先用 `video-producer visual-render scaffold` 建每条独立 composition：

```bash
video-producer visual-render scaffold <project>/render/<item>/composition \
  --width 720 --height 1280 --fps 25 --duration 5 --background '#D95B36'
```

把素材复制到 composition 的 `assets/`，在 `index.html` 的 `#stage` 内放置纸片 DOM 层。每层有固定尺寸、坐标、层级和纸张边缘/阴影；用本地 GSAP 的 paused timeline 按“基础结构 → 主体/卡片 → 连接件 → 结果”依次入场。动画应有数帧卡位感，最后至少留 0.7 秒定格。所有动作只由时间轴决定，不用 `Date.now()`、随机数、外部 CDN 或自动播放。例：

```js
// scaffold 已创建 const tl = gsap.timeline({paused:true});
tl.fromTo('#paper-1', {x:-720, rotation:-8},
  {x:0, rotation:0, duration:0.55, ease:'steps(4)'}, 0.25);
tl.fromTo('#paper-2', {y:1280, rotation:6},
  {y:0, rotation:0, duration:0.55, ease:'steps(4)'}, 1.1);
tl.fromTo('#paper-3', {x:720},
  {x:0, duration:0.55, ease:'steps(4)'}, 2.0);
```

以 `composition/index.html` 为真实可渲染画面。不要用一张完整海报做全屏淡入或 zoom 冒充逐件组装。

检查和静帧 QA：

```bash
video-producer visual-render check <project>/render/<item>/composition
video-producer visual-render preview <project>/render/<item>/composition \
  --output <project>/render/<item>/preview-v1 --at 0,0.8,1.6,2.8,4.8
```

`preview-v1/contact-sheet.jpg` 与 4.8 秒最终帧一起检查：隐喻是否一眼看懂、3–6 个大组是否清晰、黑白半调和点色是否形成层级、每层是否确实独立进入、无假字/水印/裁切越界。改版输出 `preview-v2` 等新目录，保留旧版比对。

## GATE B：呈交素材与预览

呈交每条隐喻的素材来源、联系表、最终定格帧和静帧 QA 结论。只让批准的条目进入最终渲染；修改素材或构图后重出预览并重新确认。代理批准的范围写入 `gates/gate-b.md`。

## Phase 3 确定性渲染（Stage 10）

```bash
video-producer visual-render render <project>/render/<item>/composition \
  --output <project>/render/<item>/final.mp4 --workers 1 --quality delivery
video-review <project>/render/<item>/final.mp4
```

默认交付 9:16、5 秒、720×1280、**无声** MP4。甲方要声音时先按 Brief 明确声音来源，再用 `video-producer audio-mix` / `deck-compose` 走公共音轨链；旁白必须保留用户或 main agent 提供的真人声音，不让拼贴视觉流程另造口播。逐条独立成片，不额外拼接。抽看 0、1、2、3、4.8 秒与实际播放：从空色场逐件组装、固定机位、末帧稳定、无漂移。技术检查由公共 `video-review` 执行；无声版的 `audio_absent` warning 属预期。

若 Brief 明确要生成式物体变形、光影或无法用独立纸片实现的动作，可选用 `video-producer batch-i2v --batch <gen-jobs.json>` 调公共 `aigc-video-gen`。每个 job 写 `prompt`、`first_frame`、`last_frame`、`output`、`duration`，默认无声交付时另写 `"mute": true`，脚本在生成后无损去掉音轨；记录视频模型、费用与首尾帧。这是特殊镜头的备选路径，不为普通纸片组装默认调用视频生成 API。批量脚本属于 `video-producer`，不再使用独立 `collage-broll` 工具。

## 交付

交付 `render/<item>/final.mp4` 的绝对路径、每条隐喻对应的原句、素材来源、预览联系表、GATE A/B 记录与视频 QA 结果。`composition/` 保留，便于只改入场顺序或纸片位置后确定性重渲。
