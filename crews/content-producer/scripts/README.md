# Content Producer 脚本索引

五个后期脚本借 OpenMontage 的后期工作法补我们没做的后期环节。**两个必跑、三个可选**——必跑的是发布质量硬伤，可选的是用户要才跑。

完整接入契约（落点 / 旁路条件 / 干湿分离 / 借鉴来源对照）在 `../AGENTS.md` 的 `## 脚本清单` 段；本文件只做脚本速查索引，**不重复契约**。

## 索引

| 脚本 | 用途 | 必跑/可选 | 落点 |
|------|------|---------|------|
| `normalize.py` | ffmpeg loudnorm 双 pass 把成片归一化到 -14 LUFS（抖音/视频号/B 竍竖屏发布通用标准） | **必跑** | AGENTS.md Step 5.5，exportMp4 出片后、汇报前强制跑 |
| `burn-srt.py` | ffmpeg `subtitles` 滤镜（libass）把 SRT 硬烧进画面，不可关 | 可选 | Step 5.6，仅用户明确要字幕时跑 |
| `duck.py` | ffmpeg `sidechaincompress` 旁白作 sidechain 触发 BGM 自动压低（threshold=-25dB / ratio=8:1） | 可选 | Step 5.7，仅用户要专业混音且可分轨时跑 |
| `denoise.py` | ffmpeg `afftdn`（默认）或 `arnndn`（RNN，要模型文件）给音频去环境噪声 | 可选 | Step 3.5，仅用户素材音质差时跑（AI 生成视频音轨本来就干净，跳过） |
| `interp.py` | ffmpeg `minterpolate` 补帧到 30/60fps | 可选 | Step 5.8，仅低 fps 源材（如 24fps AI 生成片）补到 30fps 顺滑 |

## 调用模板

每个脚本都支持 `--help` 查完整入参。常用模板：

```bash
# 响度归一化（必跑）
python3 ./scripts/normalize.py <video.mp4> --output <out.mp4>
# 默认 target -14 LUFS / true peak -1.5 dB / LRA 11

# 字幕硬烧（可选）
python3 ./scripts/burn-srt.py <video.mp4> <subs.srt> --output <out.mp4>
# 默认中文字幕样式 Noto Sans CJK SC 24px，可 --font-name / --font-size / --force-style 覆盖

# BGM ducking（可选，需可分轨）
# 模式 1：视频自带 BGM + 外挂旁白
python3 ./scripts/duck.py <video.mp4> <narration.mp3> --output <out.mp4>
# 模式 2：外挂 BGM + 外挂旁白
python3 ./scripts/duck.py <video.mp4> <narration.mp3> --bgm-source <bgm.mp3> --output <out.mp4>

# 音频降噪（可选，仅素材音质差时）
python3 ./scripts/denoise.py <user-footage.mp4> --output <out.mp4>
# 默认 afftdn（无外部模型依赖）；要更强降噪走 arnndn：--method arnndn --rnn-model <model.rnn>

# 补帧（可选，仅低 fps 源材）
python3 ./scripts/interp.py <video.mp4> --target-fps 30 --output <out.mp4>
# 默认 minterpolate mode=blend；要更顺走 mode=mci（motion compensated，但慢且可能出鬼影）
```

## 干湿分离约定

五个都守：输出落 `<stem>_<处理名>.mp4`（如 `output_normalized.mp4`、`output_burned.mp4`、`output_ducked.mp4`、`<stem>_denoised.mp4`、`<stem>_interp.mp4`），**不覆盖输入**。多步串联时下一步以上一步产物为输入（如 ducking 后再 normalize），原产物保留作回退。

## 旁路条件速查

- `normalize.py`：无声轨 / 音频畸变 → exit 2 报错退回 exportMp4 重生；input_i 已在 ±0.3 LUFS of target → 自动跳过渲染直接拷贝
- `burn-srt.py`：ffmpeg 不带 libass → exit 1 报错改发外挂 SRT；SRT 不存在 / 格式错 → exit 1
- `duck.py`：AI 声画同出模式混轨没法分 → 报告用户等决策；视频无声轨且没 `--bgm-source` → exit 1
- `denoise.py`：AI 生成视频音轨干净 → 跳过；ffmpeg 不带 afftdn/arnndn → exit 1；arnndn 没传 `--rnn-model` → exit 1
- `interp.py`：源 fps ≥ target fps → 自动跳过拷贝；ffmpeg 不带 minterpolate → exit 1；mci 模式出鬼影 → 退 blend 模式

## 借鉴来源（OpenMontage 吸收审计用）

- `normalize.py` ← OpenMontage Ink Theater loudness gate（必跑步骤，我们同款必跑）
- `burn-srt.py` ← OpenMontage Remotion-composer caption 烧录（Remition 内置，我们用 ffmpeg 平替）
- `duck.py` ← OpenMontage Remotion-composer mixing（Remition 内置混音，我们用 ffmpeg sidechaincompress 平替）
- `denoise.py` ← OpenMontage Ink Theater noise gate（我们只在用户素材用，AI 生成不用）
- `interp.py` ← OpenMontage Backlot 看板 frame interpolation（Remition 内置补帧，我们用 ffmpeg minterpolate 平替）

## 没吸收的 OpenMontage 能力

（上一轮已拍板，备忘——不重做）
- selector / scoring.py 7 维评分 → 已有 content-calibrator，不重
- Backlot 看板 / Remotion-composer / HyperFrames / Ink Theater 实时调色 / quality scoring → runtime 哲学对立或重复，剥掉
