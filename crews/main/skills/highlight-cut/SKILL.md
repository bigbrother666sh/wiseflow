---
name: highlight-cut
description: 基于用户提供的视频素材做高光剪辑——ASR 转写拿时间戳，自动识别高光段，ffmpeg 剪拼输出成片。仅做轻剪辑，不出脚本不烧字幕。
metadata:
  openclaw:
    emoji: "✨"
    requires:
      bins:
      - python3
      - ffmpeg
      - ffprobe
---

# 高光剪辑（highlight-cut）

## 适用场景

用户提供一段完整视频（演讲、直播、访谈、口播等），要求自动**识别精彩片段**并剪接成短成片。

典型输入：

- 一段 5–60 分钟的口播/直播/演讲视频
- 用户给的目标时长（如"剪成 60 秒的高光集锦"）

不适用：

- 用户已经明确告诉剪哪几段 → 直接用 `extract_and_concat.py` 手工抽段拼接
- 需要从零生产视频 → 走 content-producer 的 `video-product` 流程
- 需要烧字幕、加 BGM、加转场特效 → 不在本技能范围

---

## 工作区

在 `output_videos/` 下建项目文件夹：

```
output_videos/<project-en-slug>/
├── source.mp4             # 用户提供的原始视频（重命名后的副本或软链）
├── cut_plan.json          # 检测产物：[{keep, start, end, reason}]
└── highlight.mp4          # 最终高光成片
```

---

## 流程

### Step 1：检测生 cut_plan.json

```bash
python3 ./skills/highlight-cut/scripts/cut_plan.py \
    <source.mp4> \
    --mode highlight \
    --language zh \
    --output <project-dir>/cut_plan.json
```

参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mode` | `filler` | `filler` 去口气词 / `highlight` 高光剪辑 / `both` 先去口气词再标高光 |
| `--language` | `zh` | 语气词清单选择：`zh` 嗯/呃/额/唔/哎/诶/欸；`en` um/uh/uhm/er |
| `--silence-gap` | `0.6` | 静音段判据：相邻 word gap > 此秒数 |
| `--stutter-repeat` | `4` | 结巴段判据：单字重复 ≥ 此次数 |
| `--similarity-threshold` | `0.6` | 重复句段判据：句间 Jaccard > 此阈值 |
| `--output` | `cut_plan.json` | 计划产物路径 |

产物 `cut_plan.json`：

```json
{
  "ok": true,
  "source": "source.mp4",
  "duration": 1832.5,
  "mode": "highlight",
  "plan": [
    {"keep": true,  "start": 12.3,  "end": 45.8,  "reason": "highlight"},
    {"keep": false, "start": 45.8,  "end": 50.1,  "reason": "silence"},
    {"keep": true,  "start": 50.1,  "end": 88.2,  "reason": "highlight"},
    {"keep": false, "start": 88.2,  "end": 91.0,  "reason": "filler"},
    ...
  ]
}
```

`reason` 枚举：

| reason | 含义 | mode=filler 时 keep | mode=highlight 时 keep |
|--------|------|--------------------|-----------------------|
| `filler` | 语气词段 | false | — |
| `silence` | 静音段 | false | false |
| `stutter` | 结巴段 | false | — |
| `false_start` | 假起头段 | false | — |
| `repeat` | 重复句段 | false | — |
| `highlight` | 高光段 | — | true |
| `normal` | 常规段 | true | false |

> 高光判据（`detect_highlight`）：utterance 字数/时长 > 4 字/秒（zh）或 3 词/秒（en），且与全片文本 Jaccard < 0.3（"新颖段"）。

### Step 2：用户确认 cut_plan.json（关键闸门）

cut_plan.json 落盘后**必须先让用户看一眼**再剪：

- 报告：总时长、keep 段总时长、keep 段数、remove 段数、按 reason 分类的段数与累计时长
- 若 keep 段总时长与用户目标时长差距大（>20%）→ 调阈值重跑 Step 1，不要硬剪
- 用户认 plan 后才进 Step 3

### Step 3：按 cut_plan.json 剪拼成片

```bash
python3 ./skills/highlight-cut/scripts/apply_cut.py \
    <source.mp4> \
    <project-dir>/cut_plan.json \
    --output <project-dir>/highlight.mp4 \
    --fade-ms 40
```

参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--output` | `<input>_cut.mp4` | 成片输出路径 |
| `--fade-ms` | `40` | 段间 triangular fade 毫秒数（防咔点，0 关闭） |

流程：

1. 读 cut_plan.json，滤 `keep=true` 段
2. ffmpeg `-ss`/`-t` 逐段抽出（libx264 crf 20 + aac 128k + 保持源分辨率帧率）
3. 段间加 `--fade-ms` 毫秒 triangular fade 防咔点
4. ffmpeg `concat` 拼接成片，`+faststart` 优化

### Step 4：成片自检（强制闸门）

剪拼完成后**必须**跑成片自检，自检不过不得交付：

```bash
python3 ./skills/video-review/scripts/review.py <project-dir>/highlight.mp4
```

> review.py 是成片自检脚本，verdict=pass 才交付；verdict=fail 按 review 提示修。详见 `skills/video-review/SKILL.md`。

### Step 5：用户确认

向用户展示：

- 成片（发文件本体）
- 关键参数：成片时长、keep 段数、总压缩比（成片时长/源时长）
- cut_plan.json 概要（按 reason 分类的段数与累计时长）

用户确认后流程结束。后续发布由各 publish 技能执行。

---

## 依赖

| 依赖 | 来源 | 说明 |
|------|------|------|
| ffmpeg / ffprobe | 系统 | 抽 WAV、剪拼、concat |
| 火山引擎豆包语音极速版 | env `VOLC_ASR_*` | ASR 转写拿 word 级时间戳 |
| requests | 仓根 requirements.txt | 调火山 ASR HTTP API |

**火山 ASR 凭证**：需 `VOLC_ASR_APP_ID` + `VOLC_ASR_ACCESS_KEY`（旧控制台双头）或 `VOLC_ASR_APP_KEY`（新控制台单头）。未配置时 cut_plan.py 退出码 2 并提示走 viral-chaser 开通流程。

---

## 脚本清单

| 脚本 | 用途 | 退出码 |
|------|------|--------|
| `cut_plan.py` | ASR 转写 + 多层检测生 cut_plan.json | 0 成功 / 1 参数错 / 2 ASR env 未配 / 3 ffmpeg 不存在 |
| `apply_cut.py` | 按 cut_plan.json ffmpeg 剪拼成片 | 0 成功 / 1 参数错 / 3 ffmpeg 不存在 |

---

## 禁止事项（强制）

- **禁止跳过 review.py 交付**：剪拼完必须跑成片自检，verdict=pass 才交付
- **禁止硬剪不确认 plan**：cut_plan.json 落盘后必须先让用户确认 keep/remove 段再剪
- **禁止直接写 ffmpeg 命令**：所有 ffmpeg 调用走本技能脚本，不在 exec 中拼 ffmpeg 命令
