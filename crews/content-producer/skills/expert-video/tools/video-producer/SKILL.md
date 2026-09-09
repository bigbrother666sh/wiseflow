---
name: video-producer
description: 视频制作原子能力集——意图路由、故事/剧本/分镜、素材 slot 与解析、渲染、混音对齐、拼接合成、动效审计、封面。子命令范式，产物文件存在性即 checkpoint。
metadata:
  openclaw:
    emoji: 🎬
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
---

# video-producer — 工具说明

> 本文是 `expert-video` 专家包内的工具说明书，不独立出现在技能列表中。制作流程（阶段链、两闸门、workflow 选择）由包内 SKILL.md 与 `workflows/` 编排，本文只写每个子命令的输入、输出与调用方式。

**调用方式**：`video-producer <子命令> [参数...]`（wrapper 转发到 `scripts/<子命令>.py`，子命令名即脚本名，零路径拼接）。`video-producer help` 列可用子命令。

**通用约定**：

- 多数子命令第一个位置参数是 `<project_dir>`（工作区目录），产物落该目录下约定子路径。
- **产物文件存在性即 checkpoint**：子命令先查产物文件是否存在，存在则 load 不重生成（允许手改 JSON 后续跑）。
- 退出码：`0` 成功 / `1` 参数错 / `2` env 未配（如 `AWK_API_KEY`、`VOLC_ASR_*`）。

## 子命令清单

| 子命令 | 入 | 出 | 用途 |
|--------|----|----|------|
| `intent-router` | brief.md（主题/关键词/类型） | `script/intent.json`（档位+主题） | 意图路由三档：故事讲述型 narrative / 纯画面动效型 motion / 蒙太奇剪接型 montage |
| `reference-concepts` | 甲方给的参考拆解报告（可选） | `reference/concepts.md` | 据报告出 2–3 个差异化概念；不做下载/转写/抽帧 |
| `story-develop` | intent.json | `script/story.md` | idea → 故事（受众/类型复述、100–200 词梗概、人物、分场） |
| `script-write` | story.md | `script/script.md`（含 enhancement_cues 六型 + delivery_cues） | 故事 → 分场剧本（同时间同地点分一场、可拍化描述、enhancer 润色） |
| `script-self-eval` | script.md | `script/self-eval.json` | 脚本自评 N 维打分，任一维 <3 必返工 |
| `storyboard-build` | script.md | `storyboard/storyboard.json` | 剧本 → 镜头表（每镜叙事目的/机位复用/位置朝向/不写不可见） |
| `shot-decompose` | storyboard.json | `storyboard/shot_decompose.json` | 每镜拆首帧静照/尾帧静照/运动描述（variation_type 三档） |
| `character-register` | storyboard.json + brief.md | `characters/registry.json` + 三视图 png | 角色 static/dynamic features 拆分 + front/side/back（调 `siliconflow-img-gen`） |
| `slot-plan` | storyboard.json + shot_decompose.json | `slots/slot-plan.json` | 素材 slot 规划（template + hero slot + tone→slot 数） |
| `asset-resolve` | slot-plan.json | `slots/asset-resolve.json`（含 rejected_picks）+ 素材落 `raw_materials/` | 按 slot 拉素材（Fast path：多源并发搜 + 缩略图人核；调 pexels-footage / pixabay-footage / aigc-video-gen） |
| `slideshow-risk` | storyboard.json + slot-plan.json + asset-resolve.json | `slots/slideshow-risk.json` | 六维幻灯风险打分（pre-compose 闸门，≥4.0 fail） |
| `delivery-promise-lock` | storyboard.json + brief.md | `slots/delivery-promise.json` | 交付承诺八类锁定 + motion_ratio 预估 |
| `render-shot` | shot_decompose.json + characters/ + slot-picks | `render/shot-NN/` 下产物 | 按 slot 渲染（AIGC 走 `aigc-video-gen` i2v 首尾帧插值；静图走 `siliconflow-img-gen`） |
| `mix-audio` | script.md（delivery_cues） | `audio/` 目录 + `subtitles.srt` 模板 | 配音配乐四场景分流：A 人物对话声画同出 / B 旁白一次性 TTS 带字级时间戳 + 对齐 / C BGM 成片后统一生成 / D 甲方口播录音 → ASR 时间戳 → 按时间戳补素材 |
| `narration-align` | audio/narration.mp3 + audio/narration.subtitle.json | `audio/narration-segments.json` | 旁白字级时间戳对齐（优先复用 `awk-tts --enable-subtitle` 的原生时间戳，缺失时回退火山 ASR 极速版，凭据 `VOLC_ASR_*`） |
| `clip-trim` | `--input/--output/--start/--end/--speed/--sync-audio/--pre-buffer` | 切好的片段 | 精确切素材段（入点/出点/倍速/前置缓冲，视频与音频分别处理；`--pre-buffer 0.5` 防切 MP3 吞首字） |
| `audio-mix` | `--track（可重复）/--delay/--volume/--output/--duration` | 混合音频 | 多轨混音（每轨独立延时与音量） |
| `timeline-compose` | `<project_dir> --timeline timeline.json [--transition ...]` | 合成片段 | 按时间轴 JSON 调 clip-trim + audio-mix 合成（`audio_mode=concat` 出连续轨；`audio_globals` 混全片 BGM） |
| `scene-compose` | `<project_dir> --scene scene.json [--output scene-01.mp4]` | 单 Scene 片段 | 分段合成（clips + narration + dialogue → 一个 Scene）；内部调 clip-trim + audio-mix + assemble |
| `assemble` | `<project_dir> [--transition hard/fade/dissolve/xfade] [--width] [--fps] [--audio-format] [--low-memory] [--preview-duration] [--source-dir]` | `video.mp4`（+ 可选 `video-preview.mp4`） | 按序拼接成片：可选转场、分辨率/帧率归一化、自动统一音频格式（无音频段补静音）、低内存模式（ultrafast/crf28）、前 N 秒试听版 |
| `add-silent-audio` | `--input/--output/--duration/--sample-rate/--channels` | 含静音音轨的视频 | 给无音频片段补静音轨（concat 前置；assemble 内部也自动调） |
| `make-outro` | `<project_dir> --image <形象图> --slogan <文本> [--color color.json] [--duration 5] [--width 1080] [--fps 30]` | 标准比例片尾段 | 形象图 + 黑边 + 烧字幕 + 静音轨 |
| `motion-audit` | video.mp4 + delivery-promise.json | `review/motion-audit.json` | motion_led 抽查（兑付交付承诺） |
| `make-cover` | brief.md（封面主文案）+ storyboard 关键帧 | `cover.jpg` | 封面生成（调 `siliconflow-img-gen`，必含封面主文案） |

## 注意事项

- **不自己下载/转写/抽帧**：参考视频拆解归 main 的 `viral-chaser`；本工具只吃甲方给的报告或素材。
- **不引入 CLIP / torch 系本地模型**：素材匹配走 Fast path 人核缩略图。
- **图库源固定**：Pexels + Pixabay 两源，不扩充。
- **AIGC 输出路径约束**：`aigc-video-gen` 要求输出相对路径落在 `output_videos/` 下，调用时 workdir 必须是 Content Producer workspace 根。
- **env 依赖**：`AWK_API_KEY`（静帧/视频生成）、`VOLC_ASR_*`（narration-align 回退与口播录音转写）。缺 env 时子命令 exit 2，补齐属 IT engineer 职责，不要静默降级。
- **闸门不是子命令**：GATE A / GATE B 由 agent 按包内 SKILL.md 执行（呈交摘要 → 结束本轮回复 → 等甲方逐闸门批准）。

## 后期脚本（crew 级，Workspace `scripts/`）

以下五个不在本工具 wrapper 内，从 Content Producer workspace 根按 `python3 scripts/<name>.py` 调用；全部干湿分离（输出落 `<stem>_<处理名>.mp4`，不覆盖输入）。

| 脚本 | 用途 | 必跑/可选 | 落点 |
|------|------|----------|------|
| `normalize.py` | ffmpeg loudnorm 双 pass 归一化到 -14 LUFS（抖音/视频号/B站竖屏通用） | **必跑** | 成片合成后、自检与交付前 |
| `burn-srt.py` | libass 把 SRT 硬烧进画面 | 可选（Brief 或甲方要字幕时） | 归一化前后均可，串联时以上一步产物为输入 |
| `duck.py` | sidechaincompress 让旁白触发 BGM 自动压低 | 可选（要专业混音且可分轨时） | 混音阶段 |
| `denoise.py` | afftdn（默认）/ arnndn 去环境噪声 | 可选（仅甲方素材音质差时；AIGC 音轨干净跳过） | 素材入库后 |
| `interp.py` | minterpolate 补帧到 30/60fps | 可选（仅低 fps 源材） | 渲染或拼接前 |

旁路条件：`normalize.py` 无声轨/音频畸变 → exit 2 退回重生，已在 ±0.3 LUFS 内 → 自动跳过；`burn-srt.py` ffmpeg 无 libass → exit 1 改发外挂 SRT；`duck.py` 声画同出混轨不可分 → 报甲方决策；`interp.py` 源 fps ≥ 目标 → 自动跳过拷贝。
