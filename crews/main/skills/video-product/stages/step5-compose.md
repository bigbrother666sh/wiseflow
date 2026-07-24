# Step 5 / 5.5 / 6 — 合成、自检、封面（stages/ 子文档）

> 主 SKILL.md 在此段只保留导航指针，subagent 跑到 Step 5/5.5/6 时才主动 read 此文。

### Step 5 — 合成视频

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

**段间转场（可选，用户要时才开）**——默认 concat 硬切，传 `--transition crossfade` 走 ffmpeg `xfade` 链做交叉淡变：

```bash
python3 ./skills/video-product/scripts/assemble.py <project-dir>/artifacts/ \
  --output <project-dir>/video.mp4 \
  --transition crossfade --transition-duration 0.5
```

⚠️ **转场会缩成片总时长**——每段重叠 `transition-duration` 秒做交叉淡变，**成片总时长 = Σ段时长 - (段数-1) × 转场时长**。脚本规划阶段（Step 2.2.2）若预算用转场，每段时长要加 `transition-duration` 补回；review.py 的 `--target-duration` 也要按缩后总时长算，否则时长校验 critical。

转场参数：默认 0.5s 重叠（`--transition-duration` 可调），xfade 做视频轨、acrossfade 同步音频轨淡变。视频轨走 libx264 重渲染（不是 concat 的 stream copy，所以耗时长 + 损画质少），声画同出模式每段音轨保住。

旁路条件（不开转场的情况）：
- 用户没明确要"转场"/"淡变"/"crossfade"→ 走默认 concat 硬切
- 单段素材（无段间可做）→ assemble.py 自动退默认 assemble
- 段时长 ≤ 转场时长（如段 0.3s 配 transition-duration 0.5s）→ xfade offset 超段长报错，缩 transition-duration 或回硬切

合成后确认 `video.mp4` 存在且非空。

### Step 5.5 — 成片自检（强制，借鉴 OpenMontage post-render self-review + gbro Gate 3 QA）

**`video.mp4` 产出后、向用户交付前，必须强制跑 `review.py`**——不准跳过、不准肉眼看交。这是替代上一轮"裸 assemble.py 拼完就交"的脆弱闸门。

```bash
python3 ./skills/video-product/scripts/review.py <project-dir> \
  --target-duration <片段规划表「时长」列累加值> \
  --target-resolution <720x1280 | 1080x1920 | 按脚本画面比例>
```

**target-duration** 从 `script.md` 片段规划表「时长」列累加得出；**target-resolution** 按 Step 4 选的 `--ratio` + `--resolution` 推（`9:16` + `720P` → `720x1280`，`1080P` → `1080x1920`）。

`review.py` 做五件事：
1. ffprobe 全字段校验（codec / 分辨率 / fps / pix_fmt / 音轨配置）
2. 5 位抽帧（0% / 25% / 50% / 75% 100%）→ 黑帧/overlay 损检测（≥2 张黑帧 = critical）
3. 音频电平分析（mean_db / max_db，过静 < -60dB 或削顶 ≥ -1dB = critical；无声轨 = warn，需对照 pipeline 模式判断）
4. 时长 vs target（超 ±5% = critical；±1% 外 = warn）
5. 分辨率齐校（成片 vs 各段 artifacts 不齐 = critical；低于 720p = critical）

退出码即判定：
- **exit 0 → `verdict: pass`** → 进 Step 6 制作封面
- **exit 1 → `verdict: fail`** → 有 critical issue，**不准交**。按 `critical[]` 修复（重拼 / 重生成不齐段 / 重调 assemble.py）后再跑一次 review.py。最多重修 2 轮，仍 fail 则向用户复述 critical 项请求决策
- **exit 2 → `verdict: warn`** → 有 non-critical 提示，**向用户复述 warnings[] 让其决定**是重修还是接受。不准自主判定通过
- **exit 3 → 脚本本身故障**（ffprobe 缺失 / 路径错 / …）→ 不算评审结论，先修脚本

verdict JSON 默认落盘到 `<project-dir>/review/verdict.json`，抽帧落到 `<project-dir>/review/frames/`——**不进 artifacts/、不进 previews/**，自检产物跟合成产物隔离，避免混淆 assemble.py。

⚠️ **声画同出模式（默认）下 `audio_absent` warning 要对照看**：gen.py 声画同出的片有声轨是常态；若 review.py 报 `audio_absent` 且你走的是 AI 生成模式，这是 critical（gen.py 该出声没出声），降级处理退回 gen.py 重生成或补 Step 4.5 TTS。Stock Footage + `--no-audio` 模式下 `audio_absent` 是预期，warn 可放行。

### Step 6 — 制作封面

每个视频都必须配封面图。封面要求：
- **必须包含视频标题文字**，不允许纯图片封面
- 标题文字必须有设计感（字体选择、排版布局、颜色搭配）
- 竖屏封面 1080x1920
- 可以使用视频关键画面作为背景，但文字是必须元素

使用 `siliconflow-img-gen` 制作封面，保存为 `<project-dir>/cover.jpg`。

### Step 7 — 用户确认
