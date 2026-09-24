---
name: video-producer
description: 视频制作原子能力集——剧本/分镜、素材 slot 与解析、渲染、混音对齐、拼接合成、动效审计、封面。子命令范式，产物文件存在性即 checkpoint。
---

# video-producer — 工具说明

## pip-compose — 幻灯与口播小窗

```bash
video-producer pip-compose --base /absolute/slides.mp4 --presenter /absolute/presenter.mp4 --audio /absolute/narration.mp3 --output /absolute/composed.mp4 --dry-run
video-producer pip-compose --base /absolute/slides.mp4 --presenter /absolute/presenter.mp4 --audio /absolute/narration.mp3 --output /absolute/composed.mp4
```

- `--base` 与 `--output` 必填。`--presenter` 可省略，仅合旁白；`--audio` 是唯一音轨，省略时仅保留底视频音轨，**从不混入 presenter 音轨**。两者均无音轨则报错。外部音频编码为 AAC，底视频无小窗时视频流复制。
- 小窗 `--corner` 四选 top-left/top-right/bottom-left/bottom-right；默认 bottom-right。`--size` 是画布宽占比（默认 .22，范围 .1–.5），`--aspect` 宽高比（默认 1），保比放大后居中裁切，不能以此改变口型时序。
- `--margin 32`、`--radius 24`、`--border 4`、`--border-color '#ffffff'`、`--subtitle-safe 160` 均以像素计（颜色除外）；字幕安全区是全宽底部禁入带。默认适配 1080p，改尺寸后先 dry-run，超界报错。`--threads` 默认 2。
- 底视频应为方形像素、无旋转元数据、偶数尺寸、1–120fps。音轨与底视频必须等长（容差 0.12 秒）；presenter 可长于底视频（裁去尾部），短于底视频超过容差就报错，不循环/定帧/变速。先用 clip-trim 对齐入点；时长相同不等于内容同源，人工检查口型。
- `--dry-run` 只探测并输出合成计划 JSON，不生成媒体；实际输出使用临时文件，验证宽高/帧率/音视频时长后原子落盘，旁写 `.pip.json`。输入与输出必须不同，已有输出用 `--force` 显式重做。
- 返回码 0 成功、1 输入/几何/合成断言失败、2 依赖缺失。Pillow 使用仓根已有依赖；不需要新增 pip 包。

> 本文是 `expert-video` 专家包内的工具说明书，不独立出现在技能列表中。制作流程（阶段链、两闸门、workflow 选择）由包内 SKILL.md 与 `workflows/` 编排，本文只写每个子命令的输入、输出与调用方式。

**调用方式**：`video-producer <子命令> [参数...]`（wrapper 转发到 `scripts/<子命令>.py`，子命令名即脚本名，零路径拼接）。`video-producer help` 列可用子命令。

**通用约定**：

- 多数子命令第一个位置参数是 `<project_dir>`（工作区目录），产物落该目录下约定子路径。
- **产物文件存在性即 checkpoint**：子命令先查产物文件是否存在，存在则 load 不重生成（允许手改 JSON 后续跑）。
- 退出码：`0` 成功 / `1` 参数错 / `2` env 未配（如 `AWK_API_KEY`、`VOLC_ASR_*`）。

## 子命令清单

| 子命令 | 入 | 出 | 用途 |
|--------|----|----|------|
| `reference-concepts` | 甲方给的参考拆解报告（可选） | `reference/concepts.md` | 据报告出 2–3 个差异化概念；不做下载/转写/抽帧 |
| `script-write` | brief.md（创意 + 规格） | `script/script.md`（含 enhancement_cues 六型 + delivery_cues） | Brief 创意 → 分场剧本（同时间同地点分一场、可拍化描述、enhancer 润色） |
| `script-self-eval` | script.md | `script/self-eval.json` | 脚本自评 N 维打分，任一维 <3 必返工 |
| `storyboard-build` | script.md | `storyboard/storyboard.json` | 剧本 → 镜头表（每镜叙事目的/机位复用/位置朝向/不写不可见） |
| `shot-decompose` | storyboard.json | `storyboard/shot_decompose.json` | 每镜拆首帧静照/尾帧静照/运动描述（variation_type 三档） |
| `character-register` | shot_decompose.json + script.md | `characters/registry.json` + 三视图 png | 角色 static/dynamic features 拆分 + front/side/back（调 `awk-img-gen`） |
| `slot-plan` | storyboard.json + shot_decompose.json | `slots/slot-plan.json` | 素材 slot 规划（template + hero slot + tone→slot 数） |
| `asset-resolve` | slot-plan.json | `slots/asset-resolve.json`（含 rejected_picks）+ 素材落 `raw_materials/` | 按 slot 拉素材（Fast path：多源并发搜 + 缩略图人核；调 pexels-footage / pixabay-footage / aigc-video-gen） |
| `slideshow-risk` | storyboard.json + slot-plan.json + asset-resolve.json | `slots/slideshow-risk.json` | 六维幻灯风险打分（pre-compose 闸门，≥4.0 fail） |
| `delivery-promise-lock` | storyboard.json + brief.md | `slots/delivery-promise.json` | 交付承诺八类锁定 + motion_ratio 预估 |
| `render-shot` | shot_decompose.json + characters/ + slot-picks | `render/shot-NN/` 下产物 | 按 slot 渲染（AIGC 走 `aigc-video-gen` i2v 首尾帧插值；静图走 `awk-img-gen`） |
| `visual-render` | `scaffold <composition-dir> --width/--height/--duration/--fps/--background`；`check/preview/render <composition-dir>` | HTML 项目、静帧联系表或 MP4 | 共用 deck-render 锁定的 HyperFrames/GSAP/Chromium 运行时；适用产品段、标题、纸拼贴和录屏圈选。素材在 `assets/`，编辑 `index.html` 的 DOM/CSS/GSAP；预览用 `--output <空目录> --at 0,1,2`，渲染用 `--output <clip.mp4> [--workers 1] [--force]` |
| `motion-graphics` | 新项目用 `scaffold/check/preview/render`；旧项目仍可用 `<project_dir> --spec mg.json` | 单段 clip.mp4 | 新子命令直接转交 `visual-render`；旧 JSON/Pillow 模板只兼容已制作项目，不再用于新创作 |
| `batch-i2v` | `--batch gen-jobs.json [--dry-run]` | 多个 i2v MP4 | 特殊生成式动作的可选批量调度；逐条调公共 `aigc-video-gen`，job 写 `"mute": true` 时出片后无损去音轨；普通纸片组装使用 `visual-render` |
| `mix-audio` | script.md（delivery_cues） | `audio/` 目录 + `subtitles.srt` 模板 | 配音配乐四场景分流：A 人物对话声画同出 / B 旁白一次性 TTS 带字级时间戳 + 对齐 / C BGM 成片后统一生成 / D 甲方口播录音 → ASR 时间戳 → 按时间戳补素材 |
| `narration-align` | audio/narration.mp3 + audio/narration.subtitle.json | `audio/narration-segments.json` | 旁白字级时间戳对齐（**整段模式**：一条连续 narration.mp3；优先复用 `awk-tts --enable-subtitle` 的原生时间戳，缺失时回退公共 ASR 路由：火山 → 百炼） |
| `narration-layout` | `<project_dir> --plan narration_plan.json [--srt ...] [--mix ...] [--force]` | `audio/abs_starts.json` + SRT + 可选混音 | 逐句旁白排布（**逐句模式**：每句独立 mp3，与 narration-align 互补）：实测镜头时长累积起点 → 每句对齐镜头起点 + 防重叠守卫 → 逐句/末句越界断言（违反非零退出打印明细）→ SRT（样式参数化，force_style 落 abs_starts.json 供 burn-srt 引用）→ 可选一步混音（内部复用 audio-mix：N 路旁白 + BGM fade） |
| `clip-trim` | `--input/--output/--start/--end/--speed/--sync-audio/--pre-buffer/--duration/--normalize/--grade/--windows/--zoompan/--low-load` | 切好的片段 | 精确切素材段（入点/出点/倍速/前置缓冲，视频、音频、图片分别处理；`--pre-buffer 0.5` 防切 MP3 吞首字）；`--normalize 1920x1080@25` 切片即归一（scale+pad+sar+fps）；`--grade warm` 预设调色；`--windows "12.0:3.2,44.5:1.4"` 一镜多窗切后 concat；`--zoompan 1.08` 定帧缓推（视频源在 --start 取帧）；`--low-load` 低载编码（nice19/veryfast/crf18/threads2） |
| `audio-mix` | `--track（可重复）/--delay/--volume/--fadein/--fadeout/--output/--duration` | 混合音频 | 多轨混音（每轨独立延时、音量与淡入淡出；`--duration` 为硬上限：短轨补虚、超出截断） |
| `timeline-compose` | `<project_dir> --timeline timeline.json [--transition ...]` | 合成片段 | 按时间轴 JSON 调 clip-trim + audio-mix 合成（`audio_mode=concat` 出连续轨；`audio_globals` 混全片 BGM） |
| `scene-compose` | `<project_dir> --scene scene.json [--output scene-01.mp4]` | 单 Scene 片段 | 分段合成（clips + narration + dialogue → 一个 Scene）；内部调 clip-trim + audio-mix + assemble |
| `assemble` | `<project_dir> [--transition hard/fade/dissolve/xfade] [--width] [--fps] [--audio-format] [--low-memory] [--preview-duration] [--source-dir] [--manifest] [--verify-fps] [--expect-durations] [--duration-tolerance]` | `video.mp4`（+ 可选 `video-preview.mp4`） | 按序拼接成片：可选转场、分辨率/帧率归一化、自动统一音频格式（无音频段补静音）、低内存模式（ultrafast/crf28）、前 N 秒试听版；`--manifest segments.json` 显式有序段清单（手写/motion-graphics 管线产物绕开 shot-NN 命名约定）；`--verify-fps 25` 拼接后帧率断言；`--expect-durations plan.json` 逐段时长 vs 计划 ± 容差校验（兼容 shotdur.json 的 beats 形态） |
| `add-silent-audio` | `--input/--output/--duration/--sample-rate/--channels` | 含静音音轨的视频 | 给无音频片段补静音轨（concat 前置；assemble 内部也自动调） |
| `make-outro` | `<project_dir> --image <形象图> --slogan <文本> [--color color.json] [--duration 5] [--width 1080] [--fps 30] [--force]` | 标准比例片尾段 + 可编辑的 `.composition/` | 用同一 HyperFrames 视觉渲染器排版/淡入文字，再复用 `add-silent-audio` 补静音轨 |
| `motion-audit` | video.mp4 + delivery-promise.json | `review/motion-audit.json` | motion_led 抽查（兑付交付承诺） |
| `make-cover` | brief.md（封面主文案）+ storyboard 关键帧 | `cover.jpg` | 封面生成（调 `awk-img-gen`，必含封面主文案） |

## 注意事项

- **不自己下载/转写/抽帧**：参考视频拆解归 main 的 `viral-chaser`；本工具只吃甲方给的报告或素材。
- **不引入 CLIP / torch 系本地模型**：素材匹配走 Fast path 人核缩略图。
- **图库源固定**：Pexels + Pixabay 两源，不扩充。
- **AIGC 输出路径约束**：`aigc-video-gen` 要求输出相对路径落在 `output_videos/` 下，调用时 workdir 必须是 Content Producer workspace 根。
- **env 依赖**：`AWK_API_KEY`（静帧/视频生成）、`VOLC_ASR_*`（narration-align 回退与口播录音转写）。缺 env 时子命令 exit 2，补齐属 IT engineer 职责，不要静默降级。
- **闸门不是子命令**：GATE A / GATE B 由 agent 按包内 SKILL.md 执行（呈交摘要 → 结束本轮回复 → 等甲方逐闸门批准）。

## 后期处理子命令（Stage 13c 与可选后期）

同在 `video-producer` wrapper 下，调用方式与其他子命令一致：`video-producer <子命令> [参数...]`，每个都支持 `--help` 查完整入参。

| 子命令 | 用途 | 必跑/可选 | 落点 |
|--------|------|----------|------|
| `normalize` | ffmpeg loudnorm 双 pass 归一化到 -14 LUFS（抖音 / 视频号 / B站竖屏发布通用标准） | **必跑** | 阶段链 Stage 13c：成片合成后、自检与交付前强制跑 |
| `burn-srt` | libass 把 SRT 硬烧进画面（烧录后不可关） | 可选（Brief 或甲方要字幕时） | 归一化前后均可；串联时以上一步产物为输入 |
| `duck` | sidechaincompress 让旁白作 sidechain 触发 BGM 自动压低（默认 threshold -25dB / ratio 8:1） | 可选（要专业混音且可分轨时） | 混音阶段 |
| `denoise` | afftdn（默认）/ arnndn（RNN，要模型文件）去环境噪声 | 可选（仅甲方素材音质差时；AIGC 音轨本来就干净，跳过） | 素材入库后 |
| `interp` | minterpolate 补帧到 30/60fps | 可选（仅低 fps 源材，如 24fps AIGC 片） | 渲染或拼接前 |

**干湿分离（五个都守）**：输出落 `<stem>_<处理名>.mp4`（`_normalized` / `_burned` / `_ducked` / `_denoised` / `_interp`），不覆盖输入；多步串联时下一步以上一步产物为输入（如 ducking 后再 normalize），原产物保留作回退。

常用调用：

```bash
video-producer normalize <video.mp4> --output <out.mp4>          # 默认 -14 LUFS / true peak -1.5 dB / LRA 11
video-producer burn-srt <video.mp4> <subs.srt> --output <out.mp4> # 默认 Noto Sans CJK SC 24px，可 --font-name/--font-size/--force-style
video-producer duck <video.mp4> <narration.mp3> --output <out.mp4>                      # 视频自带 BGM
video-producer duck <video.mp4> <narration.mp3> --bgm-source <bgm.mp3> --output <out.mp4>  # 外挂 BGM
video-producer denoise <user-footage.mp4> --output <out.mp4>     # 更强降噪：--method arnndn --rnn-model <model.rnn>
video-producer interp <video.mp4> --target-fps 30 --output <out.mp4>  # 更顺但慢：--mode mci（高运动易出鬼影）
```

旁路条件（不满足就报错退出，不静默降级）：

- `normalize`：无声轨 / 音频畸变 → exit 2，退回 Stage 12 重生；input_i 已在 target ±0.3 LUFS 内 → 自动跳过渲染直接拷贝
- `burn-srt`：ffmpeg 不带 libass → exit 1，改发外挂 SRT；SRT 不存在或格式错 → exit 1
- `duck`：AI 声画同出模式混轨不可分 → 报甲方决策；视频无声轨且没传 `--bgm-source` → exit 1
- `denoise`：ffmpeg 不带 afftdn/arnndn → exit 1；`--method arnndn` 没传 `--rnn-model` → exit 1
- `interp`：源 fps ≥ 目标 fps → 自动跳过拷贝；ffmpeg 不带 minterpolate → exit 1；mci 出鬼影 → 退 blend

## deck-compose：deck-talk 三模式

`--mode footage --presenter 已剪口播.mp4`：从视频提取唯一音轨；`--mode avatar --avatar-job presenter.liveportrait.json`：校验任务与音视频哈希，使用原驱动音频；`--mode audio --audio 录音.wav`：无小窗。三者均必填 `--base 底画面.mp4 --output 新成片.mp4`，可调 `--corner`、`--size`、`--subtitle-safe`。底画面可为幻灯、B-roll 或混合画面，时长需与音频一致（容差 0.12 秒），禁止替换/拉伸口播。另存 `.deck-talk.json` 音频来源记录。
