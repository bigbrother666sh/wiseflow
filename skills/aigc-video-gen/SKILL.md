---
name: aigc-video-gen
description: AIGC 视频片段生成（声画同出）。直连阿里云百炼 happyhorse / 火山方舟 Seedance 候选链，支持 t2v / i2v / r2v 三种模式，每段 3–15 秒。平台自动判断写在 gen.py 里：有 MODELSTUDIO_API_KEY 走百炼，否则有 AWK_GEN_KEY 走火山，两者皆无则输出提示让 Agent 改用 pexels-footage / pixabay-footage（退出码 2）。
metadata:
  openclaw:
    emoji: 🎞️
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
---
# AIGC Video Gen — 百炼 happyhorse / 火山 Seedance 视频生成

直连阿里云百炼（DashScope）happyhorse 系列或火山方舟（Volcengine Ark）Seedance 系列端点生成视频片段（声画同出）。同模型声画同步出，无需单独 TTS。

> 本 skill 是公共能力，供 main agent（video-product 重构后的"为组装目的 AIGC 补充"）和 content-producer 共同调用。

## 平台与模型

| 平台 | 环境变量 | 模型 |
|------|---------|------|
| 阿里云百炼（优先） | `MODELSTUDIO_API_KEY`（或 `DASHSCOPE_API_KEY`） | `happyhorse-1.1-i2v`、`happyhorse-1.1-t2v`、`happyhorse-1.1-r2v` |
| 火山引擎方舟 | `AWK_GEN_KEY` | `doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-260128`、`doubao-seedance-2-0-mini-260615` |

- 两个平台的上述模型**均支持声画同出**（t2v / i2v / r2v 三种模式）。
- **平台自动判断写在 `gen.py` 里**：有 `MODELSTUDIO_API_KEY` 走百炼，否则有 `AWK_GEN_KEY` 走火山，两者皆无则输出提示让 Agent 改用 `pexels-footage` / `pixabay-footage`（退出码 2）。

### 百炼模型选择规则

按模式选首选模型，`gen.py` 自动沿候选链 fallback（happyhorse-1.1 → 1.0 → wan2.7）。

| 模式 | 首选模型 | 适用场景 |
|------|---------|---------|
| **r2v**（A.1 人物叙事 + A.3 用户参考图） | `happyhorse-1.1-r2v` | 人物故事全段（`--ref-image` 传 `character_reference.jpg`）；用户提供参考图片段 |
| **t2v**（A.2 荛围叙事） | `happyhorse-1.1-t2v` | 手机底面、数据动画、产品特写等无重要人物的场景 |
| i2v | `happyhorse-1.1-i2v` | 如果需要指定首帧的话，使用 `happyhorse-1.1-i2v`，传入图像会作为首帧图像 |

- 嫗选链（每模式一条）：`happyhorse-1.1-{mode}` → `happyhorse-1.0-{mode}` → `wan2.7-{mode}`。首选模型不可用或任务失败时 `gen.py` 自动沿链降级，无需人工干预。
- **`--model <id>` 可显式覆盖**（关闭候选链 fallback，只用该模型）；非必要不覆盖。

### WORKSPACE_ID 站点规则

配了 `WORKSPACE_ID` 时，happyhorse 走专属端点 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1`（华北2，更快）；没配则走默认 `https://dashscope.aliyuncs.com/api/v1`。

这个设置对于火山（doubao-seedance 系列模型）无效。

### 火山候选链

- 嫗选链优先级：Fast → Normal → Mini；1080P 自动跳过 Fast（Fast 仅 720p）。
- ⚠️ **火山视频生成只认 `AWK_GEN_KEY`，不回退 `ARK_API_KEY`**：`ARK_API_KEY` 是火山主模型（doubao 对话）的 key，用户可能只想用火山主模型而不用火山生成视频；若回退会误触发火山视频生成。想用火山生成视频必须单独配 `AWK_GEN_KEY`。

### 模式与时长上限

| 模式 | 触发条件 | 百炼 happyhorse-1.1 上限 | 火山 doubao-seedance 上限 |
|------|---------|---------|---------|
| t2v（文生视频） | 无 `--image`/`--ref-image`/`--ref-video` | 3–15s | 2–15s |
| i2v（图生视频） | `--image`（首帧） | 3–15s | 2–15s |
| r2v（参考生视频） | `--ref-image`（用户提供参考图） | 3–15s | 2–15s |

**脚本规划规则**（调用方约定，本脚本不强制）：
- 每个片段时长 **不得超过 15 秒**
- 超过上限的内容**必须在脚本中拆成多个片段**

## Run

通过 PATH 调用 wrapper，无需拼接脚本路径。

```bash
# 平台/模型全自动（推荐）
aigc-video-gen \
  --prompt "画面从纯色空场开始，依次滑入时钟 → 人物与剪刀 → 胶片，最终定格。固定机位。音频：纸片嗒嗰声 + BGM。" \
  --duration 5 \
  --ratio 9:16 \
  --output output_videos/<topic>/generations/01.mp4

# 显式指定模型（关闭候选链 fallback）
aigc-video-gen --model "happyhorse-1.1-i2v" --image first-frame.png --last-frame last-frame.png \
  --prompt "<声画同出描述>" --output output_videos/<topic>/generations/01.mp4

# r2v（用户提供参考图，人物故事）
aigc-video-gen --ref-image character_reference.jpg \
  --prompt "<声画同出描述>" --duration 8 --ratio 9:16 \
  --output output_videos/<topic>/generations/02.mp4
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` | required | 声画同出描述（中文，happyhorse / Seedance 对中文响应好）——旁白文案 + BGM 风格 + 环境音效 |
| `--duration` | 5 | 视频时长（秒），上限见模式表 |
| `--ratio` | `9:16` | 画面比例 |
| `--resolution` | `720P` | 分辨率：`720P` / `1080P`（火山 Fast 仅 720P） |
| `--image` | — | 首帧图像路径（i2v 模式） |
| `--last-frame` | — | 尾帧图像路径（i2v 首尾帧插值） |
| `--ref-image` | — | 用户参考图路径（r2v 模式） |
| `--ref-video` | — | 参考视频路径（如有） |
| `--model` | auto | 显式指定模型 ID（关闭候选链 fallback）；不指定则按模式走首选 + 候选链 |
| `--output` | required | 输出 MP4 路径（必须在 `output_videos/` 下，gen.py 内部 `ensure_safe_output` 校验） |

## Output

- MP4 视频片段（声画同出，含模型生成的旁白 + BGM + 环境音）
- 决策审计：workdir 下 `decisions.log`（append-only，记候选链 fallback）

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MODELSTUDIO_API_KEY` / `DASHSCOPE_API_KEY` | 阿里云百炼 API key（优先平台） |
| `AWK_GEN_KEY` | 火山方舟视频生成专用 key（不可与 `ARK_API_KEY` 混用） |
| `WORKSPACE_ID` | 可选，百炼专属端点加速 |

## Fallback 路径

`MODELSTUDIO_API_KEY` 与 `AWK_GEN_KEY` 都未配 → `gen.py` 退出码 2，Agent 应改用 `pexels-footage` / `pixabay-footage` 走 Stock Footage 模式兜底。
