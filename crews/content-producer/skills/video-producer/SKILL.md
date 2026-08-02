---
name: video-producer
description: 视频制作与片段修整。两种用法——(A) 端到端生产：从零做一支完整视频，出脚本、分镜、机位一致性、素材匹配、闸门、渲染、自检、交付；(B) 片段修整：已有几个片段要拼一下、给一个片段配音合成、稍微剪辑烧字幕等，直接用 Stage 12 工具箱（assemble/clip-trim/audio-mix/timeline-compose/scene-compose/add-silent-audio/make-outro）。接到"从零做视频""出一支完整视频""按这个脚本/主题拍片子"类需求走模式 A；接到"把这几段拼一下""给这片段配个旁白""稍微剪一下烧个字幕"类需求走模式 B。
metadata:
  openclaw:
    emoji: 🎬
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
      env:
        - AWK_API_KEY
    primaryEnv: AWK_API_KEY
---

# 视频制作与片段修整（video-producer）

## 双模式

本技能有两种用法，agent 据用户请求判断走哪条：

**模式 A：端到端生产**——用户给主题/关键词/已有脚本/已有素材中的任一组合，要求从零做一支完整视频。走 Stage 0→14 全流程：意图路由 → 故事 → 剧本 → 分镜 → 机位 → 素材 → 闸门 → 渲染 → 自检 → 交付。另可接收 **main agent 喂入的 viral-chaser 追爆报告**（作为 brief 的一部分，本技能不做视频下载/转写/抽帧——那是 viral-chaser 的活）。

**模式 B：片段修整**——用户已有几个片段要处理，不涉及从零开剧本。直接用 Stage 12 工具箱（见下方"Stage 12 工具箱"段）做修整活儿：

- 几个片段拼一下 → `assemble`（自动统一分辨率/帧率/音频格式 + 转场）
- 一个片段配个旁白/配音 → `audio-mix`（多轨混音，延时/音量可控）
- 稍微剪一下（入点/出点/倍速）→ `clip-trim`（`--pre-buffer` 避免切 MP3 吞首字）
- 按时间轴切素材+混音 → `timeline-compose`（`audio_mode=concat` 出连续轨）
- 单个 Scene 合成（片段+旁白+对白）→ `scene-compose`
- 无音频片段补静音轨 → `add-silent-audio`
- 片尾制作（形象图+黑边+烧字幕）→ `make-outro`

模式 B 不走 Stage 0→11、不走 GATE A/B、不建完整工作区目录——就在用户给的工作目录下建 `artifacts/` 落产物即可。

不适用：

- 纸拼贴 B-roll → `collage-broll`
- Manim 技术演示动画 → `manim-explainer`
- 平面设计 → `design-full`
- 基于已有素材的深度高光剪辑（去口气词/智能剪重点）→ main 的 `video-edit` / `talking-head-cut`（本技能模式 B 只做几何级修整：切段/拼接/混音/烧字幕/补轨，不做语义级剪辑）
- 视频下载与爆款分析 → main 的 `viral-chaser`

---

## 工作区目录约定

在 `output_videos/` 下建项目文件夹 `<topic-en-slug>/`：

```
output_videos/<topic-en-slug>/
├── brief.md                    # Stage 0/1 产出：意图路由 + 概念选项 + 用户选定
├── reference-driven/           # Stage 1（可选，仅当 main 喂了 viral-chaser 报告）
│   ├── viral-chaser-report.md  # main 喂入的追爆报告原档（本技能不自己跑 viral-chaser）
│   ├── concepts.md             # 据报告出的 2–3 差异化概念 + 成本 + 备选路径
│   └: 无下载产物、无 transcript、无关键帧——那些归 viral-chaser
├── script/
│   ├── intent.json             # Stage 0
│   ├── story.md                # Stage 2
│   ├── script.md               # Stage 3（含 enhancement_cues 六型 + delivery_cues）
│   ├── self-eval.json          # Stage 3 自评
│   ├── decisions.json          # 决策审计链（跨阶段累积）
├── storyboard/
│   ├── storyboard.json         # Stage 4 镜头表
│   ├── shot_decompose.json     # Stage 5 每镜首尾帧+运动+variation_type
├── characters/
│   ├── registry.json           # Stage 6 static/dynamic features
│   ├── <char-id>/front.png     # 三视图（调 siliconflow-img-gen 生成）
│   ├── <char-id>/side.png
│   └── <char-id>/back.png
├── gates/
│   ├── gate-a.md               # GATE A 文本闸门评审产物
│   ├── gate-b.md               # GATE B 素材闸门评审产物
├── slots/
│   ├── slot-plan.json          # Stage 7
│   ├── asset-resolve.json      # Stage 8（含 rejected_picks）
│   ├── slideshow-risk.json     # Stage 9 六维打分
│   ├── delivery-promise.json   # Stage 9 承诺锁定
├── render/
│   ├── shot-NN/                # Stage 10 每镜渲染产物
│   │   ├── first-frame.png     # 首帧静照（生成或素材裁切）
│   │   ├── last-frame.png      # 尾帧静照
│   │   ├── gen-run-v01.mp4     # aigc-video-gen i2v 产物
│   │   └ettings.log
│   │   └ulti-best.mp4          # 多候选择优胜出（多候选时）
├── audio/
│   ├── narration.mp3           # awk-tts 旁白
│   ├── bgm.mp3                 # BGM（pexels/pixabay 或素材库）
│   ├── subtitles.srt           # 字幕
├── artifacts/                  # Stage 12 按镜顺序的最终段
│   ├── 01_*.mp4
│   └ NN_*.mp4
├── video.mp4                   # Stage 12 拼接成片
├── review/                     # Stage 13 公共 video-review 产物
│   ├── verdict.json
│   ├── frames/
│   ├── motion-audit.json       # CP 侧 motion_led 抽查
├── cover.jpg                   # Stage 14 封面
└── final-deliver.md            # Stage 14 交付清单
```

---

## 阶段链（15 段，两闸门）

每段子命令是 `scripts/` 下一个独立 .py，agent 按本 SKILL.md 工作流逐个调。**产物文件存在性即 checkpoint**——每个子命令先查产物文件是否存在，存在则 load 不重生成（允许用户手改 JSON 后续跑）。

```
Stage 0  intent-router        意图路由 → 三档脚本模板（故事讲述型/纯画面动效型/蒙太奇剪接型）
  · 故事讲述型（narrative）——重情节、有人物弧光、含旁白；默认 3–5 镜/场
  · 纯画面动效型（motion）——重节奏感/视觉冲击/少对白；默认 5–8 镜快切
  · 蒙太奇剪接型（montage）——重氛围/抽象/纯视觉；默认 4–7 镜无叙事
Stage 1  reference-concepts   若 main 喂了 viral-chaser 报告 → 吃报告出 2–3 差异化概念；无报告跳过
Stage 2  story-develop        idea → 故事（含受众/类型显式复述，100–200 词梗概，人物，分场）
Stage 3  script-write         故事 → 分场剧本（同时间同地点分一场；可拍化描述；enhancer 润色）
Stage 3b script-self-eval     脚本自评 N 维打分，任一维 <3 必返工
Stage 4  storyboard-build     剧本 → 镜头表（每镜叙事目的/机位复用/位置朝向/不写不可见）
Stage 5  shot-decompose       每镜拆首帧静照/尾帧静照/运动描述（variation_type 三档）
Stage 6  character-register   角色三视图 front/side/back + static/dynamic features 拆分
   ────── GATE A：文本闸门（脚本+分镜+机位+角色全齐，停，发用户审）──────
Stage 7  slot-plan            素材 slot 规划（template + hero slot + tone→slot 数）
Stage 8  asset-resolve        按 slot 拉素材（Fast path：多源并发搜 + 缩略图人核 + rejected_picks 落盘）
Stage 9a slideshow-risk       六维幻灯风险打分（pre-compose 闸门，≥4.0 fail 不许进 compose）
Stage 9b delivery-promise-lock 交付承诺八类锁定 + motion_ratio 预估
   ────── GATE B：素材闸门（素材齐+计划过审，停，发用户看 contact sheet）──────
Stage 10 render-shot          按 slot 渲染（AIGC 走 aigc-video-gen i2v 首尾帧插值；静图走 siliconflow-img-gen）
Stage 11 mix-audio            配音配乐四场景分流（A 人物对话声画同出 / B 旁白一次性 TTS 带字级时间戳 + 对齐 / C BGM 成片后统一生成 / D 用户口播录音 → ASR 时间戳 → 按时间戳补素材）
Stage 12 assemble             按序拼接成片（原子工具箱：clip-trim 切段 / audio-mix 混音 / timeline-compose 时间轴合成 / assemble 拼接，agent 按 §Stage 12 工具箱场景化组合，不写死 Workflow）
Stage 13a video-review        公共 video-review 技术自检（强制闸门）
Stage 13b motion-audit       CP 侧 motion_led 抽查（兑付 delivery-promise）
Stage 14a make-cover          封面（siliconflow-img-gen，必含标题文字）
Stage 14b 交付                 向用户呈交成片+封面+关键参数
```

> Stage 0–6 全是**文本产物**，付费生成前必停——GATE A 落在这条边界上。GATE B 落在素材就绪、pre-compose 闸门通过后，确认渲染前最终计划。

---

## 子命令调用清单

| 子命令 | 入 | 出 | 用途 |
|--------|----|----|------|
| `intent-router` | brief.md（主题/关键词，或 viral-chaser 报告） | `script/intent.json`（档位+主题） | Stage 0 |
| `reference-concepts` | viral-chaser 报告（main 喂入，可选） | `reference-driven/concepts.md` | Stage 1：只吃报告出概念，不做下载/转写/抽帧；无报告跳过 |
| `story-develop` | intent.json | `script/story.md` | Stage 2 |
| `script-write` | story.md | `script/script.md`（含 enhancement_cues + delivery_cues） | Stage 3 |
| `script-self-eval` | script.md | `script/self-eval.json`（N 维分，任一维 <3 必返工） | Stage 3b |
| `storyboard-build` | script.md | `storyboard/storyboard.json` | Stage 4 |
| `shot-decompose` | storyboard.json | `storyboard/shot_decompose.json`（每镜首尾帧+运动+variation_type） | Stage 5 |
| `character-register` | storyboard.json + 人物描述 | `characters/registry.json` + 三视图 PNG | Stage 6（三视图调 siliconflow-img-gen） |
| `slot-plan` | storyboard.json + tone | `slots/slot-plan.json` | Stage 7 |
| `asset-resolve` | slot-plan.json | `slots/asset-resolve.json`（含 rejected_picks）+ 素材落 `raw_materials/` | Stage 8（调 pexels-footage / pixabay-footage / aigc-video-gen） |
| `slideshow-risk` | storyboard.json + slot-plan.json + asset-resolve.json | `slots/slideshow-risk.json`（六维分） | Stage 9a |
| `delivery-promise-lock` | storyboard.json + brief.md | `slots/delivery-promise.json`（八类锁） | Stage 9b |
| `render-shot` | shot_decompose.json + characters/ + slot-picks | `render/shot-NN/` 下产物 | Stage 10（调 aigc-video-gen i2v / siliconflow-img-gen） |
| `mix-audio` | script.md（delivery_cues） | `audio/` 目录 + `subtitles.srt` 模板 | Stage 11（四场景分流：A 声画同出 / B 旁白一次性 TTS+ASR 对齐 / C BGM 成片后生成 / D 用户口播录音 → ASR 时间戳 → 按时间戳补素材） |
| `narration-align` | audio/narration.mp3 + audio/narration.subtitle.json | `audio/narration-segments.json`（统一 segments 格式） | Stage 11b（优先复用 awk-tts --enable-subtitle 落盘的 TTS 原生字级时间戳，缺失时回退火山 ASR 极速版，凭据复用 viral-chaser 同池 `VOLC_ASR_*`） |
| `assemble` | render/ 顺序 | `video.mp4` | Stage 12（按序拼接 + 可选转场 + 可选分辨率归一化 + 自动补静音/统一音频格式） |
| `add-silent-audio` | 无音频视频片段 | 含静音音轨的视频 | Stage 12 原子工具：concat 前补齐音轨，保持连续 |
| `clip-trim` | 素材路径 + 入点/出点/倍速 | 切好的片段 | Stage 12 原子工具：精确切素材，视频和音频分别处理 |
| `audio-mix` | 多条音轨 + 各自延时/音量 | 混合音频 | Stage 12 原子工具：多轨混音 |
| `timeline-compose` | timeline.json（每段素材/入点/出点/倍速/音轨及延时） | 合成片段 | Stage 12 原子工具：按时间轴调 clip-trim + audio-mix 合成 |
| `motion-audit` | video.mp4 + delivery-promise.json | `review/motion-audit.json`（motion_led 抽查） | Stage 13b（补公共 video-review） |
| `make-cover` | brief.md（标题）+ storyboard 关键帧 | `cover.jpg` | Stage 14a（调 siliconflow-img-gen） |

> wrapper `video-producer.sh` 内部 `exec python3 "$SCRIPT_DIR/scripts/<子命令>.py" "$@"`——子命令名即脚本名，零路径拼接。

---

## 强制闸门与护栏

### GATE A（Stage 6 后）：文本闸门

文本产物全齐（脚本+分镜+机位+角色），**停下发用户审**：

- 呈交摘要：档位、场次数、镜数、角色数、关键决策（路径/模型/风格选择的备选+置信度+理由）
- **结束本轮回复**，不许在同条回复里进 Stage 7
- 批准是**逐闸门的**——早先的一句"你继续"不覆盖本闸门
- 用户要改哪段就重跑对应子命令（产物文件存在性即 checkpoint，不会重生成未改的）

### GATE B（Stage 9 后）：素材闸门

素材齐 + 计划过 slideshow_risk + delivery_promise 锁，**停下发用户看 contact sheet**：

- 呈交：slot 总数、素材就绪率、slideshow_risk 六维分与 verdict、delivery_promise 八类与 motion_ratio 预估、素材 contact sheet
- 同 GATE A 收尾纪律

### 返工与耗时上限

- 每阶段最多返工 **3 次**
- 全片最多 **3 次** send-back
- 每阶段 wall-time 默认上限 **20 分钟**——卡住要报，不要反复撞

### 不许声称没做过的事

没有 tool result 或产物文件证明，不许声称已渲染/已生成/已改动。

### 模糊意图不算确认

- 用户说"做个短片""帮我策划"**不算确认**，必须先问清楚走哪条 workflow（故事讲述型/纯画面动效型/蒙太奇剪接型）、时长、受众
- 起草/讨论脚本属对话协助，**不许调 render 工具**
- 默认**小规模**：1 场 3–5 镜，不许把模糊想法擅自扩成多场多镜；用户要扩才扩

### 决策审计链

每个选择（路径/模型/风格/音色/任何 fallback）记 `备选 + 置信度 + 理由`，跨阶段累积进 `script/decisions.json`。

---

## 依赖

| 依赖 | 来源 | 用在哪 |
|------|------|------|
| python3 / ffmpeg / ffprobe | 系统 | 各阶段脚本 |
| 公共 `aigc-video-gen` | skills/ | Stage 8/10 视频片段生成（百炼/火山声画同出，i2v 首尾帧插值） |
| 公共 `siliconflow-img-gen` | skills/ | Stage 6 角色三视图 / Stage 10 静帧 / Stage 14 封面 |
| 公共 `awk-tts` | skills/ | Stage 11B 旁白一次性 TTS（OpenClaw 内置 TTS 优先 → awk-tts fallback；加 `--enable-subtitle` 让火山单向流式 HTTP 原生返回字级时间戳，落 `narration.subtitle.json`） |
| 火山 ASR 凭据 `VOLC_ASR_*` | 实例 env | Stage 11b narration-align 回退路径 + Stage 11D 用户口播录音转写拿时间戳（复用 viral-chaser 同池：旧控制台双头 `VOLC_ASR_APP_ID`+`VOLC_ASR_ACCESS_KEY`，或新控制台单头 `VOLC_ASR_APP_KEY`） |
| 公共 `pexels-footage` / `pixabay-footage` | skills/ | Stage 8 Stock Footage 素材补充 / Stage 11C BGM 搜 |
| 公共 `video-review` | skills/ | Stage 13a 成片技术自检闸门 |
| `requests` | 仓根 requirements.txt | 各脚本 HTTP 调用 |

---

## 子命令清单（wrapper 视角）

| 子命令 | 用途 | 退出码 |
|--------|------|--------|
| `video-producer intent-router` | 意图路由三档 | 0 成功 / 1 参数错 / 2 env 未配 |
| `video-producer reference-concepts` | 吃 viral-chaser 报告出概念 | 0 成功 / 1 参数错 |
| `video-producer story-develop` | idea → 故事 | 0 成功 / 1 参数错 |
| `video-producer script-write` | 故事 → 分场剧本 | 0 成功 / 1 参数错 |
| `video-producer script-self-eval` | 脚本自评 N 维 | 0 成功 / 1 参数错 |
| `video-producer storyboard-build` | 剧本 → 镜头表 | 0 成功 / 1 参数错 |
| `video-producer shot-decompose` | 每镜拆首尾帧+运动 | 0 成功 / 1 参数错 |
| `video-producer character-register` | 角色三视图 + features | 0 成功 / 1 参数错 |
| `video-producer slot-plan` | 素材 slot 规划 | 0 成功 / 1 参数错 |
| `video-producer asset-resolve` | 按 slot 拉素材 | 0 成功 / 1 参数错 / 2 env 未配 |
| `video-producer slideshow-risk` | 六维幻灯风险打分 | 0 成功 / 1 参数错 |
| `video-producer delivery-promise-lock` | 八类承诺锁定 | 0 成功 / 1 参数错 |
| `video-producer render-shot` | 按 slot 渲染 | 0 成功 / 1 参数错 / 2 env 未配 |
| `video-producer mix-audio` | 三场景分流占位 | 0 成功 / 1 参数错 |
| `video-producer narration-align` | 旁白 ASR 对齐时间戳 | 0 成功 / 1 参数错 / 2 env 未配 |
| `video-producer assemble` | 按序拼接成片 | 0 成功 / 1 参数错 |
| `video-producer add-silent-audio` | 给无音频视频补静音轨 | 0 成功 / 1 参数错 |
| `video-producer scene-compose` | 单 Scene 分段合成 | 0 成功 / 1 参数错 |
| `video-producer make-outro` | 片尾制作 | 0 成功 / 1 参数错 |
| `video-producer clip-trim` | 切素材段 | 0 成功 / 1 参数错 |
| `video-producer audio-mix` | 多轨混音 | 0 成功 / 1 参数错 |
| `video-producer timeline-compose` | 时间轴合成 | 0 成功 / 1 参数错 |
| `video-producer motion-audit` | motion_led 抽查 | 0 成功 / 1 参数错 |
| `video-producer make-cover` | 封面（必含标题） | 0 成功 / 1 参数错 / 2 env 未配 |

---

## Stage 12 工具箱（场景化组合，不写死 Workflow）

Stage 12 段**不规定固定 Workflow**——下面四个原子工具 agent 按实际场景灵活组合。

### 原子工具清单

| 工具 | 干什么 | 关键参数 |
|------|--------|---------|
| `clip-trim` | 精确切素材段（入点/出点/倍速/前置缓冲，视频和音频分别处理） | `--input/--output/--start/--end/--speed/--sync-audio/--pre-buffer` |
| `audio-mix` | 多轨混音（每轨独立延时和音量） | `--track（可重复）/--delay/--volume/--output/--duration` |
| `timeline-compose` | 按时间轴 JSON 调 clip-trim + audio-mix 合成片段 | `<project_dir> --timeline timeline.json [--transition ...]` |
| `assemble` | 按序拼接已就绪的段 + 可选转场 + 自动分辨率归一化 + 自动统一音频格式 | `<project_dir> [--transition hard/fade/dissolve/xfade] [--width 1080] [--fps 30] [--audio-format 24000/mono] [--low-memory] [--preview-duration 30]` |
| `add-silent-audio` | 给无音频视频片段补静音音轨（concat 前置，assemble 内部也自动调） | `--input/--output/--duration/--sample-rate 24000/--channels mono` |
| `scene-compose` | 单 Scene 分段合成（片段+旁白+对白 → 一个 Scene 片段） | `<project_dir> --scene scene.json [--output scene-01.mp4]` |
| `make-outro` | 片尾制作（形象图+黑边+烧字幕+静音轨 → 标准比例片尾） | `<project_dir> --image <形象图> --slogan <文本> [--color color.json] [--duration 5] [--width 1080] [--fps 30]` |

### 场景化组合示例（非强制，agent 按实际判断）

**场景 A：无旁白直拼**
段就绪、无需切素材、无需混音——`assemble <project_dir> --transition fade` 一把过。

**场景 B：有旁白走时间轴**
旁白一次性 TTS 生成 + narration-align 拿字级时间戳后，按时间戳把各段素材对齐旁白：
1. agent 据 narration-segments.json 各段 start/end 冡素材入点/出点，写 timeline.json
2. `timeline-compose <project_dir> --timeline timeline.json` → 调 clip-trim 切段 + audio-mix 把旁白按延时叠到各段
3. 全段 BGM 走 timeline.json 的 `audio_globals` 字段混入

**场景 C：分段先合再合（scene-compose 两阶段）**
长片或某些段需独立预合（如先合 shot-01~03 为一场 Scene，再合 shot-04~06 为另一场，最后两场 concat）：
1. 写 `scene-01.json`（clips 片段列表 + narration 旁白 + dialogue 对白），跑 `scene-compose <project_dir> --scene scene-01.json --output scene-01.mp4`
2. 同样出 `scene-02.mp4`
3. 把 scene-01.mp4 / scene-02.mp4 当段素材，再跑 `assemble <project_dir> --source-dir scenes --transition fade` 合片
scene-compose 内部调 clip-trim 切段 + audio-mix 混旁白/对白 + assemble 拼段，一步出单 Scene 完整片段。

**场景 D：素材尺寸不一**
AIGC 720x1280、录屏 1080x2384、片尾 784x1176 混拼——`assemble` 传 `--width 1080 --fps 30` 归一化（scale + pad 16:9 + sar + fps 统一）后再 concat。

**场景 E：精确调速某段**
某段需 2x 快放——`clip-trim --input <段> --output <快放段> --speed 2 --sync-audio` 切好后，把快放段当段素材再拼。

**场景 F：低内存机器**
机器内存吃紧（< 4G 或容器限额）——`assemble <project_dir> --transition fade --low-memory`，preset 切 ultrafast、crf 放宽到 28，避免 x264 缓冲爆内存。打印里会标注 `低内存模式：preset=ultrafast, crf=28`。

**场景 G：先试听再合成**
长片合成前想先听前 30 秒验证旁白/BGM 平衡——`assemble <project_dir> --preview-duration 30`，成片照常落，额外产 `video-preview.mp4`（前 30 秒，`-c copy` 秒切）。试听满意后再决定是否重混。

**场景 H：AIGC 无音频段混拼 + 旁白切段吞首字**
AIGC i2v 产物常无音频流，与有音频段直拼会断续；旁白用 `clip-trim --ss` 切 MP3 会吞第一个字。`assemble` 现在自动统一音频格式（默认 24000/mono，无音频段补静音，规格不符段重采样）+ 不传 `--width/--fps` 时自动探测各段分辨率/帧率、不一时统一到最低公共规格。旁白切段走 `clip-trim --pre-buffer 0.5`，实际入点提前 0.5s 保留段头音频，逻辑入点不变。

agent 据剧本实际选场景组合，可混合多场景（如 B+E：旁白时间轴 + 某段快放）。脚本不预设顺序。

---

## 禁止事项（强制）

- **禁止跳过 GATE A/B 交付**：两闸门是工作流的一部分，呈交摘要后必须结束本轮回复等用户批
- **禁止声称没做过的事**：没有 tool result 或产物文件证明，不许声称已渲染/已生成/已改动
- **禁止把模糊想法擅自扩成多场多镜**：默认 1 场 3–5 镜，用户要扩才扩
- **禁止跳过 video-review 交付**：Stage 13a 强制闸门，verdict=pass 才进 Stage 14
- **禁止直接写 ffmpeg 命令**：所有 ffmpeg 调用走本技能子命令脚本或公共 video-edit 子命令
- **禁止自己做视频下载/转写/抽帧**：那是 viral-chaser 的活，本技能只吃 main 喂入的报告
- **禁止引入 CLIP / torch 系本地模型**：素材匹配走 Fast path 人核缩略图
- **禁止扩充图库源**：保 Pexels + Pixabay 两源
- **禁止批量生成**：逐条精做，不批量撞运气
