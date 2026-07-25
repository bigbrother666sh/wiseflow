---
name: video-product
description: 出脚本 + 三段式/分镜结构 + Gate 0 关键帧确认 + 预算估算 + 逐段 AI 生成 + 合成自检 + 封面，完整视频生产主力技能。三条平行路径（collage-broll/html-video/manim-explainer）的编排入口。
metadata:
  openclaw:
    emoji: "🎬"
    requires:
      bins:
      - python3
      - ffmpeg
      - ffprobe
---

# Video Product

content-producer 的视频生产主力技能。负责**出脚本 → Gate 0 关键帧确认 → 预算估算 → 逐段 AI 生成/素材组装 → 合成 → 成片自检 → 封面 → 用户确认**全链路。

> **三条平行路径的编排入口**：本技能是默认主链。若内容类型更适合拼贴动画/模板驱动/科学动画，先择 `collage-broll` / `html-video` / `manim-explainer`，再回本技能做合成兜底。

---

## 工作区目录准备

在 `output_videos/` 下创建项目文件夹，如 `output_videos/<topic-en-slug>/`，作为 project-dir。

> 作为 viral-chaser 技能的后续步骤时，不必执行此步骤，viral-chaser 已创建好编排目录。

工作区结构：

```
<project-dir>/
├── raw_article.md       # 输入文章/追爆报告原文
├── script.md            # 定稿脚本（含项目音色设定 + 片段规划表）
├── character_reference.jpg  # 人物故事模式的人物定妆照（A.1）
├── keyframes/           # Gate 0 关键帧静图 + contact sheet（不参与合成）
├── calibration/         # content-calibrator 打分+预测落盘
├── budget.json          # 预算估算 + 实际累计
├── raw_materials/       # 用户提供的原始素材
├── downloads/           # Stock Footage 下载
├── generations/         # AIGC 产物
├── artifacts/           # 最终定稿片段（按编号排序）
│   ├── 01_xxx.mp4
│   ├── 02_xxx.mp4
│   └── ...
├── previews/            # 逐段确认用压缩预览（不参与合成）
│   └ NN_xxx_preview.mp4
├── review/              # 成片自检产物（verdict.json + frames/）
└── video.mp4            # 最终成品
```

---

## 工作流总览

```
Step 1 输入解析 ──→ Step 2 脚本创作定稿 ──→ Gate 0 关键帧确认 ──→ Step 2.4 打分 ──→ Step 2.5 预算 ──→ Step 3 用户素材 ──→ Step 4 视频生产 ──→ Step 5 合成 ──→ Step 5.5 自检 ──→ Step 6 封面 ──→ Step 7 用户确认
```

每个 Step 的细节文档在 `stages/` 下，subagent 跑到对应阶段时按需 read：

| 阶段 | 子文档 | 何时读 |
|------|--------|--------|
| Step 1 输入来源与预处理 | `stages/input-sources.md` | 收到输入时 |
| Step 2 脚本创作定稿 | `stages/step2-script.md` | 进脚本阶段 |
| 模型选型与时长限制 | `stages/model-selection.md` | Step 2 拆段 + Step 4 生产 |
| Step 3 用户素材预处理 | `stages/step3-user-assets.md` | 用户提供了素材 |
| Step 4 视频素材生产 | `stages/step4-assets.md` | 进生产阶段 |
| Step 5/5.5/6 合成/自检/封面 | `stages/step5-compose.md` | 进合成阶段 |
| 禁止事项 + 注意事项 | `stages/prohibitions-notes.md` | 全流程遵守 |

**强制顺序**：Step 3 优先于所有其他生产步骤——无论 AI 生成还是 Stock Footage，用户素材都先处理。

---

## Step 1 — 输入解析

读 `stages/input-sources.md`。四种来源：文章链接 / 追爆报告（viral-chaser 后续）/ 文字主题 / 本地文件。产出 `topic-en-slug` + `raw_article.md`。

---

## Step 2 — 脚本创作定稿

读 `stages/step2-script.md` + `stages/model-selection.md`。产出 `script.md`，含**项目音色设定** + **片段规划表**（每段 ≤15s，对应一次 AI 生成或一个用户素材）。

脚本定稿流程：

1. 撰写脚本（正常流程走三段式；viral-chaser 后续按追爆报告拆解的原视频结构）
2. 片段拆分——含项目音色设定 + 片段规划表
3. **slideshow-risk 自检**——规划表写完后、发用户定稿前，对规划表过 3 维清单（repetition/weak-motion/typography-overreliance），命中任一维度重写该段
4. 发用户确认脚本原文，用户确认后存 `script.md`
5. **Gate 0 — 关键帧 contact sheet 确认**（定稿后、生产前强制）——逐段 `siliconflow-img-gen` 出静图拼 contact sheet 发用户全段确认，改文字免费、重生一张图远比重跑一段视频便宜
6. **Step 2.4 打分+盲预测**（content-calibrator）——`script.md` 落盘后做一次盲打分 + 盲预测，落 `calibration/`
7. **Step 2.5 预算估算**——Gate 0 通过 + 打分通过后，输出全片预算估算（API 调用次数/耗时/费用），**等用户明确回复"开跑"才进 Step 4**

Gate 0 / 打分 / 预算各有旁路条件，详见 `stages/step2-script.md`。

---

## Step 3 — 用户素材预处理

读 `stages/step3-user-assets.md`。**优先于所有其他生产步骤**——无论哪种模式，用户素材都先处理。

- 视频素材：探测时长 → 检查音轨（无音轨或要补配音走 3.3）→ 按片段编号命名落 `artifacts/`
- 图片素材：**禁止直接转视频**，仅作 AI 生成参考图或搜索风格参考

补配音走公共 `siliconflow-tts`（优先 OpenClaw 内置 TTS，不可用时回退）。

---

## Step 4 — 视频素材生产

读 `stages/step4-assets.md` + `stages/model-selection.md`。**只生产脚本中标注「AI生成」的片段**，用户素材片段已在 Step 3 就位。

### 模式 A：AI 生成模式（默认）

走公共 `aigc-video-gen`（PATH 调用）。平台自动判断写在 `aigc-video-gen` 里：有 `MODELSTUDIO_API_KEY` 走百炼，否则有 `AWK_GEN_KEY` 走火山，两者皆无退出码 2 提示改用 Stock Footage。

按片段规划逐段生成，串行执行（下一段等上一段下载完成再发）：

- **A.1 人物故事模式**（人物叙事类片段必用）——第 0 步 `siliconflow-img-gen` 生人物定妆照 `character_reference.jpg`，**每段都以它为 `--ref-image` 走 r2v**（首选 `happyhorse-1.1-r2v` 沿链 fallback）。每段生成后必须发用户确认，确认后才生成下一段。
- **A.2 t2v 模式**（氛围叙事类片段）——不传 `--image`，只写 prompt。适合手机底面、数据动画、产品特写等不含重要人物的场景。
- **A.3 r2v 模式**（仅用户提供参考图时）——对应 Step 3.4 静态图片作为参考，传 `--ref-image`。

模型选型、候选链、时长上限、参数说明、生产中常见错误与重试策略见 `stages/step4-assets.md`。

### 模式 B：Stock Footage 托底模式（`aigc-video-gen` 退出码 2 时）

素材搜集优先级：`pexels-footage`（9:16 竖屏）→ `pixabay-footage`（Pexels 不可用或无结果时）。一次只下载一个视频，时长精准匹配，下载后按片段编号重命名。

质量自检（仅 Stock Footage 模式）：

```bash
python3 ./skills/video-product/scripts/check.py <project-dir>/
```

每下载一段素材后运行一次，直到 `verdict: "accepted"` 且时长满足。

### Step 4.5 — TTS 配音（仅 Stock Footage 模式或 AI 生成无音频时）

> **AI 生成模式下通常跳过**：声画同出模型已同步生成音频。

优先 OpenClaw 内置 TTS（`tts_generate`），不可用时回退公共 `siliconflow-tts`（需 `SILICONFLOW_API_KEY`）。需先创建 `tts_requirement.md`，可用语音清单见 `stages/step4-assets.md`。

---

## Step 5 — 合成视频

读 `stages/step5-compose.md`。

**⚠️ 合成前必须先清理废弃片段**：逐段确认产生的废弃版本（如 `02_choose_path.v1_bad.mp4`）和正式片段共用同一数字前缀，assemble.py 会把它们一起拼进去。合成前移到 `artifacts/_deprecated/`（assemble.py 非递归扫描，子目录不参与）或删除。

```bash
python3 ./skills/video-product/scripts/assemble.py <project-dir>/artifacts/ --output <project-dir>/video.mp4
```

可选段间转场——`--transition crossfade` 走 ffmpeg `xfade` 链做交叉淡变（段 ≥ 2 才生效，单段或 ffmpeg 不带 xfade 时退硬切不鲗）。⚠️ 转场会缩成片总时长，脚本规划阶段若预算用转场，每段时长要加 `transition-duration` 补回；review.py 的 `--target-duration` 也要按缩后总时长算。

合成规则：
- **无外部音频文件**（AI 声画同出模式常态）：assemble.py 保留每段视频自带音轨拼接；个别无音轨的片段自动补静音以保持拼接布局一致
- **有外部音频文件**（`speech.mp3` 等，Stock Footage + TTS 模式）：外部音频替换视频原音轨
- 不烧录字幕

assemble.py 按文件名数字前缀（`01_`、`02_`、`03_`…）顺序拼接，同一前缀内按文件名字典序。

---

## Step 5.5 — 成片自检（强制闸门）

读 `stages/step5-compose.md`。`video.mp4` 产出后、向用户交付前，**必须强制跑 `review.py`**——不准跳过、不准肉眼看交。

```bash
python3 ./skills/video-review/scripts/review.py <project-dir> \
  --target-duration <片段规划表「时长」列累加值> \
  --target-resolution <720x1280 | 1080x1920 | 按脚本画面比例>
```

退出码即判定：
- **exit 0 → `verdict: pass`** → 进 Step 6 制作封面
- **exit 1 → `verdict: fail`** → 有 critical issue，不准交。按 `critical[]` 修复后再跑一次 review.py。最多重修 2 轮，仍 fail 则向用户复述 critical 项请求决策
- **exit 2 → `verdict: warn`** → 有 non-critical 提示，向用户复述 `warnings[]` 让其决定是重修还是接受。不准自主判定通过
- **exit 3 → 脚本本身故障**（ffprobe 缺失 / 路径错等）→ 不算评审结论，先修脚本

verdict JSON 默认落盘 `<project-dir>/review/verdict.json`，抽帧落 `<project-dir>/review/frames/`——不进 artifacts/、不进 previews/，自检产物跟合成产物隔离。

⚠️ **声画同出模式（默认）下 `audio_absent` warning 要对照看**：gen.py 声画同出的片有声轨是常态；若 review.py 报 `audio_absent` 且你走的是 AI 生成模式，这是 critical（该出声没出声），降级处理退回重生成或补 Step 4.5 TTS。Stock Footage + `--no-audio` 模式下 `audio_absent` 是预期，warn 可放行。

---

## Step 6 — 制作封面

每个视频都必须配封面图。封面要求：
- **必须包含视频标题文字**，不允许纯图片封面
- 标题文字必须有设计感（字体选择、排版布局、颜色搭配）
- 竖屏封面 1080x1920
- 可以使用视频关键画面作为背景，但文字是必须元素

使用 `siliconflow-img-gen` 制作封面，保存为 `<project-dir>/cover.jpg`。

---

## Step 7 — 用户确认

向用户展示：
- 成品视频（发文件本体）
- 封面图（发文件本体）
- 关键参数（时长、分辨率、片段数）
- `budget.json` 的 expected vs actual variance（供后续 calibration 校准未来项目的预测准度）

用户确认后，流程结束。后续发布由 media-operator 调用对应发布技能执行。

---

## 脚本清单

| 脚本 | 文件名 | 用途 | 使用场景 |
|------|--------|------|---------|
| 视频片段生成 | `aigc-video-gen`（公共 skill，PATH 调用） | 直连火山/百炼端点生成视频片段（声画同出）；百炼按模式走候选链（happyhorse-1.1→1.0→wan2.7），火山走 Fast→Normal→Mini | AI 生成模式（默认） |
| 预览压缩 | `./skills/video-product/scripts/compress_preview.py` | 把视频压到 ≤16MB 用于聊天确认（产物仅用于确认，不参与合成） | 逐段确认 |
| 片段合成 | `./skills/video-product/scripts/assemble.py` | 视频+音频合成 MP4，可选 `--transition crossfade` 段间溶接 | 所有模式 |
| 成片自检 | `./skills/video-review/scripts/review.py` | ffprobe + 抽帧黑帧扫 + 音频电平 + 时长分辨率一致性，verdict pass/fail/warn | 合成后强制闸门（交付前必跑） |
| 素材自检 | `./skills/video-product/scripts/check.py` | 检查素材质量与时长缺口 | 仅 Stock Footage 模式 |
| TTS 语音合成 | `siliconflow-tts`（公共 skill，PATH 调用） | 读取 tts_requirement.md 生成配音 | 仅 OpenClaw 内置 TTS 不可用时 |

---

## 禁止事项（强制）

违反以下任何一条都会导致系统死机或产出异常，**必须严格遵守**：

- **禁止直接写 ffmpeg 命令**：不得在 exec 中直接调用 ffmpeg/ffprobe，也不得写 Python 脚本内嵌 ffmpeg 调用。所有视频处理一律通过 `./skills/video-product/scripts/` 下的标准化脚本完成
- **禁止从静态图生成视频**：不得将 JPEG/PNG 等静态图片通过 ffmpeg 转为 MP4。用户提供的静态图片仅作为 AI 生成参考图或搜索风格参考
- **禁止跳过 review.py 交付**：`video.mp4` 产出后必须先跑 `review.py`，verdict = pass 才能进制作封面环节；fail 必须修后重审，不准交；warn 向用户复述让其决定

更多注意事项见 `stages/prohibitions-notes.md`。
