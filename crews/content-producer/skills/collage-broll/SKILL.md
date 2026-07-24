---
name: collage-broll
description: 将约 5 秒口播文稿、观点句或抽象概念做成高级 editorial halftone paper-collage / 半调纸拼贴 B-roll。用户说"collage b-roll""纸拼贴 b-roll""半调拼贴""拼贴风格配画面""用这段文稿做拼贴动画""gbro-collage-broll"，或希望把一句文稿转成拼贴视觉隐喻时，必须使用此 skill。强制采用三阶段审批：先只提视觉隐喻，用户确认后用 siliconflow-img-gen 生成彩色拼贴静帧，静帧再次确认后用 gen.py（i2v 首尾帧插值）组装动画。视频生成走百炼 happyhorse-1.1-i2v 候选链（沿链 fallback）或火山 Seedance（视 env 配置），不调 Gemini Omni。
metadata:
  openclaw:
    emoji: 🗞️
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
      env:
        - AWK_API_KEY
    primaryEnv: AWK_API_KEY
    homepage: https://www.volcengine.com/docs/82379/1541523
---

# Collage B-roll（纸拼贴组装动画）

把一句约 5 秒的口播压成一个 sharp visual idea，再做成高级编辑风纸拼贴组装动画。

本 skill 由 gbro-collage-broll 适配而来——三闸门审批节奏 + assemble-from-empty prompt 写法保留，但所有外部依赖换到 xiaobei 语境：

| 原膜（gbro） | 本 skill（xiaobei） |
|------|------|
| Gemini Omni Flash（视频） | gen.py i2v 首尾帧插值（百炼 happyhorse-1.1-i2v 沿链 / 火山 Seedance） |
| Codex 内置 `image_gen`（静帧） | `siliconflow-img-gen` 技能（Seedream doubao-seedream-4.5） |
| GEMINI_API_KEY + google-genai SDK | AWK_API_KEY（图像）/ MODELSTUDIO_API_KEY 或 AWK_GEN_KEY（视频） |
| `~/hyperframes-projects/.omni-venv/` 独立 venv | 仓根 `requirements.txt` + `scripts/apply-addons.sh` 统一装，不留独立 venv |
| `~/hyperframes-projects/YYYY-MM-DD-collage-broll-标题/` | `output_videos/<topic-en-slug>/`（xiaobei 路径契约） |
| Veo 旧脚本兼容 | 不带——我们一开始就是 Seedance / happyhorse，无 Veo 遗产 |

默认链路：

1. 只设计视觉隐喻，等待用户确认（Gate 1）
2. 只生成最终静帧，等待用户确认（Gate 2）
3. 自动调 gen.py 生成视频并完成 QA（Gate 3）

这两个确认闸门是工作流的一部分。它们让用户把注意力放在审美和方向上，同时避免错误隐喻或错误静帧直接消耗视频生成成本。

## 首次使用：环境自检

每次触发本 skill 时，进入 Gate 1 之前先运行自检脚本：

```bash
bash <本skill目录>/scripts/check_setup.sh
```

全部通过则直接开始 Gate 1，不要向用户重复配置信息。任何一项失败时，视为首次使用：不进入 Gate 1，先向用户输出下面的配置指南（只列出缺失项），等用户确认配置完成后重新自检。

### 配置指南（按缺失项输出）

1. **AWK_API_KEY 未设置**（Gate 2 静帧生成要）
   到 [火山方舟控制台](https://console.volcengine.com/ark) 创建 API key，然后写入 shell 配置：

   ```bash
   echo 'export AWK_API_KEY="你的key"' >> ~/.zshrc && source ~/.zshrc
   ```

2. **MODELSTUDIO_API_KEY / AWK_GEN_KEY 都未设置**（Gate 3 视频生成要）
   - 百炼走 `MODELSTUDIO_API_KEY`（[阿里云百炼控制台](https://dashscope.console.aliyun.com/)）
   - 火山走 `AWK_GEN_KEY`（火山方舟，同 AWK_API_KEY 控制台但需开视频生成权限）
   - 两个都没配 → gen.py 退出码 2，向用户报告并按 gbro 原话提示"改用 pexels-footage / pixabay-footage 兜底"（但拼贴动画用 stock footage 没意义，实际是等用户配 key）

3. **ffmpeg / ffprobe 缺失**
   macOS：`brew install ffmpeg`；Debian/Ubuntu：`sudo apt install ffmpeg`。

4. **Python 环境缺失或版本过旧**（需要 >= 3.10）
   macOS：`brew install python3`；或从 python.org 安装。

## 强制审批协议

### Gate 1：隐喻确认

收到文稿后，先提视觉隐喻，不生成图片、不生成视频、不调用任何视频模型。

向用户交付每条的：

- 核心意思
- 情绪
- 一句话视觉命题
- 3–6 个关键物件
- 建议底色与局部点色
- 预期组装顺序

然后明确停下，等待用户回复"可以""通过""全部通过"或给出逐条修改意见。

如果用户只确认部分编号，只让通过的条目进入 Gate 2；未通过条目继续修改隐喻。

### Gate 2：静帧确认

隐喻确认后，才写 visual spec 和 imagegen prompt，并用 `siliconflow-img-gen` 技能生成最终静帧。

把原图保存到项目目录，生成带编号的静帧 contact sheet，向用户展示并再次停下。此阶段仍然不调 gen.py，也不生成视频。

如果用户只确认部分静帧，只让通过的条目进入 Gate 3；需要修改的静帧先重生并重新确认。

### Gate 3：视频生成

静帧确认后，不再询问使用哪个视频模型，直接用本 skill 自带的 `scripts/run_gate3.py` 调 `gen.py` 走 i2v 首尾帧插值——默认走百炼 `happyhorse-1.1-i2v`（沿链 fallback 到 1.0 → wan2.7），百炼没配走火山 Seedance Fast → Normal → Mini。只有用户明确指定其他模型时才 `gen.py --model <id>` 覆盖。

## 成功标准

- 一句话只表达一个清晰隐喻
- 同一批画面有统一设计语言，但不强制全部蓝底
- 背景是强烈、平坦、均匀的色场，可按语意变化
- 主体以黑白 halftone photographic cut-outs 为骨架
- 关键卡片、按钮、胶片、规则册等允许使用红、黄、青、橙、紫、奶油白等彩色纸张
- 所有纸片有清晰裁切边、奶油白 keyline、低透明度柔和阴影和纸张颗粒
- 动作是 assemble-from-empty，而不是轻微漂移、晃动或慢 zoom
- 无字幕、无口播全文、无 logo、无水印、无 UI
- 默认交付 9:16、5 秒、720×1280、有声画同出（gen.py 默认 `audio: true`，旁白/BGM/环境音写在 prompt 里）MP4

## 什么时候不要用

- 需要精确控制图层、遮挡、镜头穿越或可编辑时间线：改用分层动画工具
- 只需要视频提示词，不需要生成成片：直接写 prompt 即可，不用走本流程
- 需要真实人物产品广告或口播演员：不要走本拼贴流程
- 用户明确要可逐层修改的透明素材：本 skill 默认不拆透明图层

## 默认项目目录

用 xiaobei 路径契约——落在 `output_videos/` 下，名 `<topic-en-slug>`：

```text
output_videos/<topic-en-slug>/
├── brief.md                    # 文稿 + Gate 1 隐喻清单
├── visual-spec.json            # Gate 2 视觉规格
├── imagegen-prompts.md         # Gate 2 Seedream prompt 留档
├── gen-jobs.json               # Gate 3 gen.py 批量调用清单
├── gate2-qa.md                 # 静帧 QA 结论
├── gate3-qa.md                 # 视频 QA 结论
├── still-contact-sheet.jpg     # Gate 2 静帧总图
├── video-contact-sheet-all.jpg # Gate 3 全部成片逐秒抽帧
├── end-frame-comparison-all.jpg # 确认静帧 vs 视频末帧并排
├── 01-<concept-slug>/
│   ├── gen-prompt.txt          # gen.py --prompt 内容（声画同出描述）
│   ├── frames/
│   │   ├── still.png           # Gate 2 确认的完成帧（原图）
│   │   ├── last-frame.png      # 统一裁到 720x1280 的尾帧
│   │   └first-frame.png        # 纯色空首帧（同底色 hex）
│   └gen-runs/run-v01/
│       ├── final-5s.mp4        # gen.py 产物
│       ├── final-5s-noaudio.mp4 # 强制无声交付（拼贴动画无声）
│       ├── contact-sheet.jpg   # 逐秒抽帧总图
│       └ video-last-frame.jpg
│       └ end-frame-comparison.jpg
└── 02-<concept-slug>/...
```

## Phase 1：设计视觉隐喻

先把文稿压成一个视觉命题。

提取：

- 核心意思：观众最终要看懂什么
- 情绪：冷静、惊讶、紧迫、豁然开朗、荒诞、反讽
- 动作动词：打开、连接、漏掉、装订、归档、点亮、压缩、分叉、组装
- 可视化隐喻：机器、时钟、胶片、档案柜、控制台、规则册、漏斗、轨道、棋子

不要把文稿逐字放进画面。默认一条文稿只做一个隐喻，控制在 3–6 个关键物件；元素过多会让语意变弱，也会让 i2v 组装不稳定。

批量隐喻优先形成前后叙事：例如先表现手工消耗与经验流失，再表现规范沉淀与人机分工。

### Gate 1 输出示例

```text
1. 核心意思：经验每次都在重复消耗
   视觉隐喻：熟练剪辑师围着巨大的胶片时钟逐帧裁切，时钟走完一圈却只得到一小段成片
   关键物件：胶片时钟、剪辑师、剪刀、短胶片
   色彩：焦橙底，奶油白与浅青点色
   组装顺序：时钟 → 人物与剪刀 → 胶片 → 最终短输出
```

输出后停下等待确认。

## Phase 2：生成彩色拼贴静帧

隐喻确认后，先写自包含的 `visual-spec.json`，再写 imagegen prompt。

### Visual spec

```json
{
  "script_meaning": "",
  "visual_metaphor": "",
  "style_signature": "flat bold color field, mixed black-and-white halftone cut-outs and colored cardstock accents, crisp cut edges, cream keylines, soft paper shadows, editorial paper collage",
  "aspect_ratio": "9:16",
  "color_field": {
    "background_hex": "",
    "accent_colors": [],
    "paper_grain": "fine uncoated-paper fiber"
  },
  "elements": [
    {
      "what": "",
      "role": "",
      "motion": "",
      "placement": ""
    }
  ],
  "composition": {
    "layout": "",
    "negative_space": "",
    "final_frame": ""
  },
  "motion_plan": "structure first, subject or cards second, action and result last",
  "avoid": "typography, readable letters, numerals, logos, watermark, UI, subtitles, glossy 3D, photoreal environment"
}
```

### 色彩规则

不要把 cobalt blue 当成唯一默认值。根据语意挑选强色场，并在一批作品中保持"同设计语言、不同底色"：

- 焦橙 / 红：时间消耗、劳动、紧迫
- 芥末黄：工具、警示、经验漏失
- 墨绿：认知、审美、系统重置
- 深紫：规范、沉淀、长期记忆
- 青绿：判断、协作、自动执行

主体可以黑白半调为主，但局部彩色纸张必须服务信息层级，不要为了彩色而彩色。

### Imagegen prompt 模板（siliconflow-img-gen / Seedream）

用 `siliconflow-img-gen` 技能（Seedream doubao-seedream-4.5，fallback doubao-seedream-5.0-lite）：

```bash
siliconflow-img-gen --prompt "<下面整段>" --image-size 1600x2848 --out-dir <project>/01-<slug>/frames/
```

Prompt 模板（英文，Seedream 对英文 prompt 响应更好）：

```text
Use case: ads-marketing
Asset type: final still frame for a 9:16 image-to-video B-roll clip
Primary request: Create a finished editorial paper-collage image expressing [一句话视觉命题].
Scene/backdrop: perfectly flat [颜色] paper field [hex] with subtle uncoated paper fiber.
Style/medium: premium editorial stop-motion paper collage; black-and-white halftone photographic cut-outs mixed with selective [点色] colored cardstock.
Composition/framing: vertical 9:16 locked poster frame; central subject within the middle 70 percent; generous clean color-field negative space; 3–6 large separable paper groups for later assemble-from-empty animation.
Materials/textures: visible printed halftone dots, crisp machine-cut edges, thin warm-cream paper keylines, soft low-opacity physical drop shadows.
Constraints: [本条隐喻必须一眼看懂的关系].
Avoid: no typography, no readable letters, no numerals, no logos, no watermark, no UI, no subtitles, no glossy 3D, no photoreal environment, no clutter.
```

Seedream 不支持参考图锁定风格（gbro 原膜靠 Codex `image_gen` 的参考图能力），所以"同设计语言"靠**同一批用同一 `style_signature` 字串 + 同一 `color_field` 范围**在 prompt 里复用，不靠参考图。

### 静帧 QA

- 隐喻是否一眼看懂
- 主体是否集中
- 是否有假字、logo、水印或 UI
- 是否保留足够纯色场，方便从空场组装
- 是否是 3–6 个清晰大组，而不是满屏碎片
- 同一批是否统一质感但有色彩变化

将通过 QA 的原图复制到 `<item>/frames/still.png`，生成带编号的静帧 contact sheet，展示给用户并停下等待 Gate 2 确认。静帧 QA 结论写入 `<project>/gate2-qa.md`。

如果用户要求重生部分静帧，重生后生成 `still-contact-sheet-v2.jpg`（后续轮次递增 v3、v4…），保留旧版 contact sheet 不覆盖，方便对比。

拼静帧 contact sheet 用 ffmpeg tile：

```bash
ffmpeg -y -pattern_type glob -i "<project>/*/frames/still.png" \
  -vf "scale=270:480,tile=5x1" \
  -frames:v 1 <project>/still-contact-sheet.jpg
```

段数 > 5 时分多行（`tile=5x2`、`5x3`…）。

## Phase 3：用 gen.py i2v 生成视频

### 1. 准备首尾帧

保留 imagegen 原图 `still.png`，再统一尾帧到 720x1280（gen.py i2v 收 720P/1080P，默认 720P）：

```bash
ffmpeg -y -i <item>/frames/still.png \
  -vf "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280" \
  <item>/frames/last-frame.png
```

首帧默认是与尾帧相同底色的纯色空纸面（assemble-from-empty 的核心——从空场开始组装）：

```bash
ffmpeg -y -f lavfi -i color=c=0x<HEX>:s=720x1280 \
  -frames:v 1 <item>/frames/first-frame.png
```

如果用户明确要求不从完全空白开始，首帧才保留一个基础物件。

### 2. 写 gen.py 动画 prompt

动作顺序默认采用：

```text
基础结构 → 人物或关键卡片 → 连接件 → 动作 → 最终结果
```

gen.py 的 `--prompt` 是**声画同出**描述（中文，happyhorse / Seedance 对中文响应好），不是 gbro 原膜的英文长 prompt。要把 gbro 原膜的 Omni prompt 段**转译**成 gen.py 风格：

gbro 原膜 Omni prompt（英文长段）→ gen.py prompt（中文声画同出描述）转译规则：
- `Image 1 is the exact empty first frame` → 不写（gen.py `--image first-frame.png` `--last-frame last-frame.png` 显式传首尾帧，不在 prompt 里写）
- `Image 2 is the exact completed last frame` → 不写（同上）
- 组装顺序段 → 中文化："画面从纯色空场开始，依次滑入 [基础结构] → [人物/卡片] → [连接件] → [动作]，最终定格在已确认的完成构图"
- `No scene cuts, no camera movement, no zoom, no morphing` → 中文化："固定机位，无切镜、无 zoom、无变形"
- `no text, no letters, no numbers, no logos, no watermark, no UI` → 中文化："画面无文字、无 logo、无水印、无 UI"
- 声画同出补充（gbro 原膜是无声，gen.py 默认有声）："音频：纸片滑入的嗒嗰声 + 卡位时的咔嗒声 + 最终定格的短促 BGM 收尾"

gen.py prompt 模板：

```text
画面从纯色空场开始，依次滑入 [基础结构] → [人物/卡片] → [连接件] → [动作]，最终定格在已确认的完成构图。固定机位，无切镜、无 zoom、无变形。画面无文字、无 logo、无水印、无 UI。音频：纸片滑入的嗒嗰声 + 卡位时的咔嗒声 + 最终定格的短促 BGM 收尾。
```

每条 prompt 都要明确 `--image first-frame.png` 是空首帧、`--last-frame last-frame.png` 是确认过的完成帧。最终构图必须贴近 last-frame，不让模型自由改造尾帧。

### 3. 检查 gen.py 运行环境

gen.py 自带 env 自动判平台（MODELSTUDIO_API_KEY 优先百炼，AWK_GEN_KEY 走火山），不需要独立 venv 或 SDK 安装——仓根 `requirements.txt` + `scripts/apply-addons.sh` 统一装。自检脚本 `check_setup.sh` 只探 ffmpeg / ffprobe / AWK_API_KEY / 视频平台 key，不探 venv。

### 4. 批量调用 gen.py

创建 `gen-jobs.json`。每个 job 用首尾帧插值（i2v 模式）：

```json
{
  "prompt": "<gen.py prompt 中文>",
  "first_frame": "<item>/frames/first-frame.png",
  "last_frame": "<item>/frames/last-frame.png",
  "output": "<item>/gen-runs/run-v01/final-5s.mp4",
  "ratio": "9:16",
  "resolution": "720P",
  "duration": 5
}
```

使用本 skill 自带脚本批量调 gen.py：

```bash
python3 <本skill目录>/scripts/run_gate3.py --batch <project>/gen-jobs.json
```

脚本默认走 gen.py i2v 模式（首尾帧插值），百炼 happyhorse-1.1-i2v 沿链 fallback（1.1 → 1.0 → wan2.7），百炼没配走火山 Seedance Fast → Normal → Mini。gen.py 内部已带候选链 fallback + decisions.log 落盘，本脚本只做批量调度。

如果出现 i2v 不收首尾帧的报错（gen.py 退出码非 0），检查 first-frame.png / last-frame.png 是否真存在、是否 720x1280——gen.py 的 `ensure_safe_output()` 要求相对路径在 `output_videos/` 下，**调 gen.py 时 workdir 必须是 workspace 根**。

### 5. 强制无声交付

拼贴动画是无声的（gbro 原膜默认无声），但 gen.py 声画同出模式会出声。Gate 3 出片后用 ffmpeg 抽无声版交付：

```bash
ffmpeg -y -i <run>/final-5s.mp4 \
  -map 0:v:0 -c:v copy -an \
  <run>/final-5s-noaudio.mp4
```

默认交付 `final-5s-noaudio.mp4`，保留原始 `final-5s.mp4` 作为中间产物。

如果用户明确要"带声"——拼贴动画的纸片嗰声 + BGM 是 gen.py 声画同出出的，可能挺贴——就不抽无声，直接交付 `final-5s.mp4`。但默认走无声（保 gbro 原膜契约）。

## 视频 QA

不要只看尾帧，必须检查组装过程和最终落位。

### Contact sheet

```bash
ffmpeg -y -i <run>/final-5s-noaudio.mp4 \
  -vf "fps=1,scale=270:480,tile=5x1" \
  -frames:v 1 <run>/contact-sheet.jpg
```

通过标准：

- 首帧接近纯色空场；边缘轻微提前露出纸片可以接受
- 中段能看到结构、人物或卡片逐步进入，而不是整体淡入
- 没有切镜、zoom、3D 化或写实场景漂移
- 没有假字、logo、水印或 UI
- 最终帧与确认静帧一致；轻微姿态或细节漂移（如人物姿势微变、小零件增减）只要不影响隐喻语义即可判通过，不要为此重跑
- 成片为 720×1280、有声画同出（`final-5s.mp4`）或无声（`final-5s-noaudio.mp4`）、5 秒

另外抽取视频末帧，与确认静帧并排生成 `end-frame-comparison.jpg`。批量项目再合并三张总览图：

- `video-contact-sheet-all.jpg`：全部成片逐秒抽帧
- `video-first-frame-all.jpg`：全部成片实际首帧，验证真的从空色场开始
- `end-frame-comparison-all.jpg`：确认静帧与视频末帧并排对照

逐条 QA 结论（含带瑕疵通过的判定理由）写入 `<project>/gate3-qa.md`。

### 常见问题

- 首帧边缘提前露出：轻微可接受；严格空场需求改用更坚定的 first-frame（纯色 + 边缘 padding）
- 组装感弱：缩短元素数量，并把 prompt 改为明确的逐件"滑入 / 卡位"顺序
- 尾帧漂移：强化 prompt 里"最终定格在已确认的完成构图"，gen.py i2v 的 last-frame 权重高
- 出现假字：先回到静帧重生（Seedream 也可能出假字），不要直接用视频 prompt 修补
- 个别视频失败：只重跑对应 job，不要重跑已经通过的条目
- i2v 报错（gen.py 退出码非 0）：检查首尾帧是否 720x1280、是否真存在、workdir 是否 workspace 根

## 默认交付

向用户交付：

- 每条 `<item>/gen-runs/run-v01/final-5s-noaudio.mp4`（或 `final-5s.mp4` 若用户要带声）
- 每条 contact sheet
- 批量总 contact sheet
- 最终帧对照图
- 一句说明每条文稿如何转成视觉隐喻

如果成片问题来自 gen.py i2v 的生成限制（组装感弱 / 尾帧漂移），直接说明；只有需要精确图层控制时，才建议切换到其他方案（如 HyperFrames，但我们不内置 HyperFrames）。

## 脚本清单

| 脚本 | 文件名 | 用途 |
|------|--------|------|
| 环境自检 | `scripts/check_setup.sh` | 探 ffmpeg / ffprobe / AWK_API_KEY / 视频平台 key，全过 exit 0，否则 exit 1 报缺失项 |
| Gate 3 批量调度 | `scripts/run_gate3.py` | 读 gen-jobs.json，逐条调 gen.py i2v 模式（首尾帧插值），落产物 + decisions.log |

visual-spec.json 生成、imagegen prompt 拼装、contact sheet 拼图、首尾帧 ffmpeg 处理——这些靠 agent 直接调 `siliconflow-img-gen` + ffmpeg 完成，不单独上脚本（agent 直接调更灵活，且避免脚本重复造轮子）。

## 没吸收的 gbro 原膜能力

- Gemini Omni Flash / google-genai SDK / Files API 上传 → 全换成 gen.py i2v + siliconflow-img-gen
- Veo 旧脚本兼容 → 不带（无 Veo 遗产）
- `~/hyperframes-projects/.omni-venv/` 独立 venv → 不用（仓根 requirements.txt 统一装）
- Codex 内置 `image_gen` 参考图锁定风格 → 不能（Seedream 无参考图锁定，靠 prompt 复用同一 style_signature + color_field）
