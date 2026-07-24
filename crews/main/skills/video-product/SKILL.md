---
name: TODO:rename
description: 将已有视频素材拼接成完整视频，支持通过AIGC或者`pexels-footage`、`pixabay-footage`进行素材补充以及按需补充配音配乐。
metadata:
  openclaw:
    emoji: "🎥"
    requires:
      bins:
      - python3
      - ffmpeg
      - ffprobe
---

# TODO:rename

---

## 工作区目录准备

在 `output_videos/` 下创建项目文件夹，如 `output_videos/<topic-en-slug>/`，作为 project-dir。

> 作为 viral-chaser 技能的后续步骤时，不必执行此步骤，因为 viral-chaser 已经创建好了编排目录。

工作区结构：

```
<project-dir>/
├── raw_materials/        # 用户提供的原始内容，或者从别处拷贝过来的复用素材
├── downloads/            # 下载的内容
├── generations/          # AIGC产物
├── artifacts/            # 最终定稿需要使用的素材片段
│   ├── 01_xxx.mp4        # 按编号排序的视频片段
│   ├── 02_xxx.mp4
│   └── ...
├── previews/              # 逐段确认用压缩预览（仅用于发聊天确认，不参与合成）
│   └── NN_xxx_preview.mp4
└── video.mp4              # 最终成品
```

---

## AIGC补充生成视频片段（按需）

视频素材优先使用 `gen.py` 脚本生成。

### 平台与模型

| 平台 | 环境变量 | 模型 |
|------|---------|------|
| 阿里云百炼（优先） | `MODELSTUDIO_API_KEY`（或 `DASHSCOPE_API_KEY`） | `happyhorse-1.1-i2v`、`happyhorse-1.1-t2v`、`happyhorse-1.1-r2v` |
| 火山引擎方舟 | `AWK_GEN_KEY` | `doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-260128`、`doubao-seedance-2-0-mini-260615` |

- 两个平台的上述模型**均支持声画同出**（t2v / i2v / r2v 三种模式）。
- **平台自动判断写在 `gen.py` 里**：有 `MODELSTUDIO_API_KEY` 走百炼，否则有 `AWK_GEN_KEY` 走火山，两者皆无则输出提示让 Agent 改用 `pexels-footage`/`pixabay-footage`（退出码 2）。

### 百炼模型选择规则

按模式选首选模型，`gen.py` 自动沿候选链 fallback（happyhorse-1.1 → 1.0 → wan2.7）。

| 模式 | 首选模型 | 适用场景 |
|------|---------|---------|
| **r2v**（A.1 人物叙事 + A.3 用户参考图） | `happyhorse-1.1-r2v` | A.1 人物故事全段（`--ref-image` 传 `character_reference.jpg`）；A.3 用户提供参考图片段（Step 3.4） |
| **t2v**（A.2 氛围叙事） | `happyhorse-1.1-t2v` | 手机底面、数据动画、产品特写等无重要人物的场景 |
| i2v | `happyhorse-1.1-i2v` | 如果需要指定首帧的话，使用`happyhorse-1.1-i2v`，传入图像会作为首帧图像。|

- 候选链（每模式一条）：`happyhorse-1.1-{mode}` → `happyhorse-1.0-{mode}` → `wan2.7-{mode}`。首选模型不可用或任务失败时 `gen.py` 自动沿链降级，无需人工干预。
- **`--model <id>` 可显式覆盖**（关闭候选链 fallback，只用该模型）；非必要不覆盖。

### WORKSPACE_ID 端点规则

配了 `WORKSPACE_ID` 时，happyhorse 走专属端点 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1`（华北2，更快）；没配则走默认 `https://dashscope.aliyuncs.com/api/v1`。

这个设置对于火山（doubao-seedance系列模型）无效。

### 火山候选链

- 候选链优先级：Fast → Normal → Mini；1080P 自动跳过 Fast（Fast 仅 720p）。
- ⚠️ **火山视频生成只认 `AWK_GEN_KEY`，不回退 `ARK_API_KEY`**：`ARK_API_KEY` 是火山主模型（doubao 对话）的 key，用户可能只想用火山主模型而不用火山生成视频；若回退会误触发火山视频生成。想用火山生成视频必须单独配 `AWK_GEN_KEY`。

### 模式与时长上限

| 模式 | 触发条件 | 百炼happyhorse-1.1上限 | 火山doubao-seedance上限 |
|------|---------|---------|---------|
| t2v（文生视频） | 无 `--image`/`--ref-image`/`--ref-video` | 3–15s | 2–15s |
| i2v（图生视频） | `--image`（首帧） | 3–15s | 2–15s |
| r2v（参考生视频） | `--ref-image`（用户提供参考图） | 3–15s | 2–15s |

**脚本规划规则**：
- 每个片段时长 **不得超过 15 秒**
- 超过上限的内容**必须在脚本中拆成多个片段**

### 当无AIGC模型可用时，或用户明确要求不使用AIGC时，走 Stock Footage 模式

素材搜集优先级：
1. ****：从 Pexels 免费素材库搜索下载（9:16 竖屏）
2. ****：Pexels 不可用或无结果时，从 Pixabay 下载

**素材下载规则**：
- 一次只下载一个视频
- 时长精准匹配（根据脚本片段时长设置 `--min-duration` / `--max-duration`）
- 下载后按脚本片段编号重命名

### 补配音配乐（用户素材需要时）

当用户素材需要补充音频时：

1. **确定目标时长**：以素材视频的实际时长为准
2. **生成配音**：
   - 优先使用 OpenClaw 内置 TTS 工具（`tts_generate`）
   - 不可用时回退到 `tts.py`（需先创建 `tts_requirement.md`）
   - 生成的音频时长必须与视频时长匹配（TTS 语速可微调以适配）
3. **合成片段**：将配音与视频合成为带音轨的片段

```bash
python3 ./skills/video-product/scripts/assemble.py <project-dir>/artifacts/ --output <project-dir>/artifacts/<NN>_final.mp4
```

#### TTS 配音（仅 Stock Footage 模式或 AI 生成无音频时）

> **AI 生成模式下通常跳过此步骤**：Wan 系列的 `audio: true` 已同步生成音频。

当需要单独生成 TTS 时：

**优先使用 OpenClaw 内置 TTS 工具**（`tts_generate` 或 agent 内置语音合成能力）。

OpenClaw 内置 TTS 不可用时，回退到本地脚本(要求环境变量已经配置SILICONFLOW_API_KEY）：

```bash
python3 ./skills/video-product/scripts/tts.py <project-dir>/ --overwrite
```

需先创建 `tts_requirement.md`：

```markdown
# 配音需求

## 配音文案
<!-- 需要朗读的纯文本，不含 markdown 标题、注释或镜头说明 -->

## 语音要求
- 音色：fnlp/MOSS-TTSD-v0.5:benjamin
- 语速：1.0
- 语气：自然、有吸引力
```

可用语音:

| Voice ID | 说明 |
|----------|------|
| `fnlp/MOSS-TTSD-v0.5:benjamin` | 幽默男声，语速较慢，推荐 |
| `fnlp/MOSS-TTSD-v0.5:charles` | 激昂男声，适合广告 |
| `fnlp/MOSS-TTSD-v0.5:claire` | 清澈女声，推荐 |
| `fnlp/MOSS-TTSD-v0.5:david` | 清脆男声 |
| `fnlp/MOSS-TTSD-v0.5:diana` | 可爱女声，娃娃音 |

---

## 合成成品

调用 assemble.py 将所有片段按编号顺序拼接为最终成品。

**⚠️ 合成前必须先清理废弃片段**：逐段确认过程中产生的废弃版本（如 `02_choose_path.v1_bad.mp4`、`03_traffic_master.v1_old.mp4` 等）**和正式片段共用同一数字前缀**，assemble.py 会把它们当成对应段一起拼进去，导致成片重复/错乱。合成前先删除或移出 `artifacts/`：

```bash
# 把废弃版本移到 artifacts/_deprecated/ 子目录（assemble.py 非递归扫描，子目录不参与拼接）
mkdir -p <project-dir>/artifacts/_deprecated
mv <project-dir>/artifacts/*.v*_*.mp4 <project-dir>/artifacts/_deprecated/ 2>/dev/null
# 或直接删除：rm <project-dir>/artifacts/*.v*_*.mp4
```

清理后确认 `artifacts/` 顶层只剩 `01_*.mp4 … NN_*.mp4` 每段一个正式片段，再合成：

```bash
python3 ./skills/video-product/scripts/assemble.py <project-dir>/artifacts/ --output <project-dir>/video.mp4
```

合成规则：
- **无外部音频文件**（AI 声画同出模式常态）：assemble.py 保留每段视频自带音轨拼接；个别无音轨的片段自动补静音以保持拼接布局一致，不会把成片变无声
- **有外部音频文件**（`speech.mp3` 等，Stock Footage + TTS 模式）：外部音频替换视频原音轨
- 不烧录字幕

assemble.py 按文件名数字前缀（`01_`、`02_`、`03_`…）顺序拼接，同一前缀内按文件名字典序。

合成后确认 `video.mp4` 存在且非空。

---

## 制作封面

每个视频都必须配封面图。封面要求：
- **必须包含视频标题文字**，不允许纯图片封面
- 标题文字必须有设计感（字体选择、排版布局、颜色搭配）
- 竖屏封面 1080x1920
- 可以使用视频关键画面作为背景，但文字是必须元素

使用 `siliconflow-img-gen` 制作封面，保存为 `<project-dir>/cover.jpg`。

---

## 用户确认

向用户展示：
- 成品视频（发文件本体）
- 封面图（发文件本体）
- 关键参数（时长、分辨率、片段数）

用户确认后，流程结束。后续发布由 media-operator 调用对应发布技能执行。

---

## 脚本清单

| 脚本 | 文件名 | 用途 | 使用场景 |
|------|--------|------|---------|
| 视频片段生成 | `./skills/video-product/scripts/gen.py` | 直连火山/百炼端点生成视频片段（声画同出）；百炼按模式走候选链（happyhorse-1.1→1.0→wan2.7），火山走 Fast→Normal→Mini | AI 生成模式（默认） |
| 预览压缩 | `./skills/video-product/scripts/compress_preview.py` | 把视频压到 ≤16MB 用于聊天确认（产物仅用于确认，不参与合成） | 人物故事模式逐段确认 |
| 片段合成 | `./skills/video-product/scripts/assemble.py` | 视频+音频合成 MP4 | 所有模式 |
| 素材自检 | `./skills/video-product/scripts/check.py` | 检查素材质量与时长缺口 | 仅 Stock Footage 模式 |
| TTS 语音合成 | `./skills/video-product/scripts/tts.py` | 读取 tts_requirement.md 生成配音 | 仅 OpenClaw 内置 TTS 不可用时 |

---

## 禁止事项（强制）

违反以下任何一条都会导致系统死机或产出异常，**必须严格遵守**：

- **禁止直接写 ffmpeg 命令**：不得在 exec 中直接调用 ffmpeg/ffprobe，也不得写 Python 脚本内嵌 ffmpeg 调用。所有视频处理一律通过 `./skills/video-product/scripts/` 下的标准化脚本完成
- **禁止从静态图生成视频**：不得将 JPEG/PNG 等静态图片通过 ffmpeg 转为 MP4。用户提供的静态图片仅作为 AI 生成参考图或搜索风格参考
