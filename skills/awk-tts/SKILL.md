---
name: awk-tts
description: 火山方舟豆包语音合成 2.0（seed-tts-2.0 字符版）文本转语音。生成 MP3/PCM/WAV/OGG_OPUS 旁白音频，凭据走 VOLC_TTS_*（旧控制台双头）或 VOLC_TTS_APP_KEY（新控制台单头），与 viral-chaser 火山 ASR 同控制台开通。
metadata:
  openclaw:
    emoji: 🔊
    requires:
      bins:
        - python3
        - ffprobe
      env:
        - VOLC_TTS_APP_ID
        - VOLC_TTS_ACCESS_KEY
    primaryEnv: VOLC_TTS_ACCESS_KEY
    homepage: https://www.volcengine.com/docs/6561/1598757
---

# 火山方舟豆包语音合成（awk-tts）

走火山 openspeech v3 单向流式接口合成旁白音频。

## 优先级约定（强制）

**优先使用 OpenClaw 内置 TTS 工具**（`tts_generate` 或 agent 内置语音合成能力）。

OpenClaw 内置 TTS 不可用时，回退到本 skill 的本地脚本（要求环境变量已经配置火山 TTS 凭据）。

> 即：本 skill 的 `scripts/tts.py` 是 **fallback 路径**，不应首选。调用方在 SKILL.md 里描述 TTS 环节时，须照此优先级写明，不许把本脚本写成第一选择。

## 首次使用：开通火山语音合成

火山豆包语音合成 2.0 与本仓 `viral-chaser`（火山 ASR）同控制台、同范式开通：

1. 登火山引擎控制台 → 左侧「开通管理」→ **「语音模型」**选项卡
2. 拉到最下找 **「Doubao-语音合成-2.0」** → 点击「立即使用」
3. 在跳转页选 **「试用」**（一开始送 2 万字符，可先用，后续再点开通付费）
4. 在该页面拿三项凭据：**APP ID**（数字）、**Access Token**、**Secret Key**

**给小贝的凭据**（按控制台版本二选一）：

| 控制台版本 | 给小贝的变量 | 备注 |
|---------|------------|------|
| 旧控制台双头 | `VOLC_TTS_APP_ID`（数字 APP ID）+ `VOLC_TTS_ACCESS_KEY`（Access Token） | 与 viral-chaser ASR 同对范式，**Secret Key 不给** |
| 新控制台单头 | `VOLC_TTS_APP_KEY`（APP Key） | 旧控制台账号不要把 Secret Key 填到这里 |

> 鉴权二选一（脚本优先旧控制台双头）。脚本自动判：同时给出 `VOLC_TTS_APP_ID`+`VOLC_TTS_ACCESS_KEY` 走旧双头；否则用 `VOLC_TTS_APP_KEY` 走新单头。

> 应该 spawn IT engineer subagent 写入实例环境变量，**不要自己写环境变量文件**，it-engineer具有相关背景知识。

## Run

**Do NOT set env vars inline**（例如 `VOLC_TTS_ACCESS_KEY=... python3 ...`）。env var 已在系统环境里，inline 赋值会破坏 exec 权限检查。

```bash
# 基础中文旁白，默认落 ./tmp/awk-tts-<ts>/speech.mp3
awk-tts --text "大家好，欢迎来到今天的视频。"

# 从文件读文本
awk-tts --text-file ./scripts/script.txt --out-dir ./assets/audio

# Fragment 工作流：读 tts_requirement.md，抽音色/语速设置，
# 出 speech.mp3 + speech.json 到 ./fragments/01-hook/artifacts/
awk-tts ./fragments/01-hook/ --overwrite

# 指定音色 + 格式 + 精确输出路径
awk-tts \
  --text "This is a demo voiceover." \
  --voice "en_female_dacey_uranus_bigtts" \
  --format wav \
  --sample-rate 44100 \
  --output ./assets/audio/demo.wav
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `fragment_dir` | — | Optional fragment directory under `fragments/`; when set, reads `tts_requirement.md` and defaults output to `artifacts/speech.<format>` |
| `--text` | — | Text to synthesize. Required unless `--text-file` or `fragment_dir` is set |
| `--text-file` | — | UTF-8 text file to synthesize. Must be relative and under `scripts`, `assets`, `tmp`, `output_videos`, or `fragments` |
| `--voice` | `zh_female_shuangkuaisisi_uranus_bigtts` | Speaker ID（火山音色，见下表） |
| `--format` | `mp3` | Audio format: `mp3`, `pcm`, `ogg_opus`, `wav` |
| `--sample-rate` | — | Optional sample rate: 8000/16000/22050/24000/32000/44100/48000 |
| `--speech-rate` | — | Optional speech rate, range `-50`–`100`（0=默认, 100=2x, -50=0.5x） |
| `--loudness` | — | Optional loudness, range `-50`–`100`（0=默认） |
| `--context-text` | — | Optional 情感控制上下文（如 '用撒娇甜蜜的语气'，仅 2.0/克隆音色支持） |
| `--output` | — | Exact output file path under `assets/audio`, `tmp`, `output_videos`, or `fragments` |
| `--out-dir` | `./tmp/awk-tts-<ts>` | Output directory under `assets/audio`, `tmp`, `output_videos`, or `fragments` when `--output` is not set |
| `--overwrite` | off | Overwrite existing output audio/metadata files |
| `--no-asr-check` | off | Skip ASR self-check after TTS generation |

## Recommended voices（官方 2.0 音色，`_uranus_bigtts` 后缀）

| Speaker ID | 名称 | 场景 |
|-----------|------|------|
| `zh_female_shuangkuaisisi_uranus_bigtts` | 爽快思思 2.0 ⭐默认 | 通用 |
| `zh_female_cancan_uranus_bigtts` | 知性灿灿 2.0 | 角色扮演 |
| `zh_female_tianmeixiaoyuan_uranus_bigtts` | 甜美小源 2.0 | 通用 |
| `zh_female_vv_uranus_bigtts` | Vivi 2.0 | 多语种通用（中/日/印尼/墨西哥西语） |
| `zh_female_xiaohe_uranus_bigtts` | 小何 2.0 | 通用 |
| `zh_female_kefunvsheng_uranus_bigtts` | 暖阳女声 2.0 | 客服 |
| `zh_male_m191_uranus_bigtts` | 舟 2.0 | 通用男声 |
| `zh_male_taocheng_uranus_bigtts` | 小天 2.0 | 通用男声 |
| `en_female_dacey_uranus_bigtts` | Dacey | 多语种（英） |
| `en_male_tim_uranus_bigtts` | Tim | 多语种（英） |

> 克隆音色（`S_xxx` 开头）走 `seed-icl-2.0` 资源 ID，脚本自动路由，需 `model_type=4`（脚本自动加）。

## Output

- Audio file: `speech.<format>` 或 `--output` 指定路径
- Metadata file: `speech.json`（同目录），含：
  - `duration`: 音频时长（秒，via ffprobe）
  - `provider` / `resource_id` / `speaker` / `format` / `text_chars` / `audio_bytes` / `file`

Fragment 工作流模式下，脚本读 `tts_requirement.md`、抽 `## 配音文案` / `## Voiceover Text` 段、读音色/语速设置、直接写到 fragment 的 `artifacts/` 目录。脚本合成时跳过 markdown heading、注释、音色设置行。

## ASR Self-Check

合成后自动跑 ASR 自检（除非 `--no-asr-check`）：

1. 调火山录音文件极速版 ASR（资源 ID `volc.bigasr.auc_turbo`，与 viral-chaser 同 `VOLC_ASR_*` 凭据池）
2. 用 Jaccard 相似度对比转写文本与输入文本
3. 阈值 **0.5**（50%）——实测 50% Jaccard 已够实用质量；过高阈值会假阴性
4. 结果打印 `PASS` / `WARN`，不 abort

ASR 凭据未配置时静默跳过自检。

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VOLC_TTS_APP_ID` + `VOLC_TTS_ACCESS_KEY` | 旧控制台双头鉴权（数字 APP ID + Access Token，优先） |
| `VOLC_TTS_APP_KEY` | 新控制台单头鉴权（APP Key） |
| `VOLC_TTS_API_BASE` | Optional API base override，默认 `https://openspeech.bytedance.com/api/v3` |
| `VOLC_TTS_RESOURCE_ID` | Optional resource ID override，默认 `seed-tts-2.0`（按 speaker 特征自动路由） |
| `VOLC_ASR_APP_ID` + `VOLC_ASR_ACCESS_KEY` | ASR 自检用旧控制台双头（与 viral-chaser 同凭据池复用） |
| `VOLC_ASR_APP_KEY` | ASR 自检用新控制台单头 |
| `VOLC_ASR_RESOURCE_ID` | Optional ASR 资源 ID override，默认 `volc.bigasr.auc_turbo` |
