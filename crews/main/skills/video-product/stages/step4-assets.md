# Step 4 — 视频素材生产（stages/ 子文档）

> 主 SKILL.md 在此段只保留导航指针 + 前置条件，subagent 跑到 Step 4 时才主动 read 此文。

> 前置条件：Step 3 已完成，用户素材已就位并编号放入 artifacts/。

**只生产脚本中标注为「AI生成」的片段**，用户素材片段已在 Step 3 处理完毕。逐片段调用 `gen.py`，脚本按平台自动选模型（百炼按模式走候选链，火山走 Fast→Normal→Mini 候选链）。

#### 模式 A：AI 生成模式（gen.py，默认）

按脚本片段规划，**根据 Step 2.5 的人物一致性要求，逐个生成**。每片段一条 `gen.py` 调用，串行执行（下一段等上一段下载完成再发）。

##### 模式 A.1：人物故事模式（人物叙事类片段必用，参考图保持人物一致）

人物一致性靠**同一张参考图**：第 0 步生成人物定妆照，**每段都以它为 `--ref-image` 走 r2v**（首选 `happyhorse-1.1-r2v`（沿链 fallback））。**不做段间首尾帧链式生成**（实测意义不大）：每段独立生成，画面不强制连续，叙事连续靠 prompt 文字承接。

**完整流程**：

**第 0 步：生成人物参考图**（整段故事只做一次）

用 `siliconflow-img-gen` 技能生成人物定妆照，保存为 `<project-dir>/character_reference.jpg`。这张图定义人物的脸/发型/年龄/服装，后续所有片段都以它为 `--ref-image` 保持人物一致。

**每段生成（统一 r2v + 参考图）**

```bash
python3 ./skills/video-product/scripts/gen.py \
  --prompt "画面描述：The same character from the reference image — keep face/hair/age/outfit EXACTLY identical to the reference. 本段场景与动作描述。音频描述" \
  --ref-image "<project-dir>/character_reference.jpg" \
  --ratio 9:16 --resolution 720P --duration 8 \
  --output <project-dir>/artifacts/NN_xxx.mp4
```

全段同一张参考图，首选 `happyhorse-1.1-r2v`（沿链 fallback）。**不传 `--image` / `--prev-segment`**（r2v 不收首帧）。

**每段生成后必须发给用户确认，确认后才生成下一段**（确认流程见下文「逐段确认」）。各段独立生成，下一段不依赖上一段产物。

**逐段确认流程**（每段视频生成后执行）：

1. 用 `compress_preview.py` 把该段视频处理成可发送的预览：
   ```bash
   python3 ./skills/video-product/scripts/compress_preview.py <project-dir>/artifacts/NN_xxx.mp4 \
     --output <project-dir>/previews/NN_xxx_preview.mp4
   ```
   - 输入 ≤16MB → 脚本直接拷贝，exit 0，打印 `[ok] under-limit`
   - 输入 >16MB → 脚本逐级压缩到 ≤16MB，exit 0，打印 `[ok] compressed`
   - 压缩失败 → exit 1，打印 `[fail]`
2. 根据脚本结果向用户确认：
   - exit 0 → **把预览视频文件本体直接发到聊天里**（`previews/NN_xxx_preview.mp4`），请用户确认本段画面
   - exit 1 → **把原始片段路径发给用户**，告知"压缩失败，请在本机打开 `<project-dir>/artifacts/NN_xxx.mp4` 查看"，请用户确认
3. 用户确认本段 → 继续生成下一段（独立生成，不带 `--prev-segment`）；用户要求重做 → 调整 prompt 重新生成本段（不推进到下一段）

⚠️ **`previews/` 下的压缩预览仅用于给用户确认，绝不参与最终合成**。`assemble.py` 只扫描 `artifacts/`，`previews/` 自然被排除；预览文件名带 `_preview` 后缀进一步避免混淆。**禁止把预览放进 `artifacts/`**。

**人物故事模式必须遵守**：

- **先生成人物参考图，再逐段生成视频**；**每段都用 `--ref-image`（同一张 `character_reference.jpg`），全程 r2v（`happyhorse-1.1-r2v`），不传 `--image` / `--prev-segment`**
- **逐段确认**：每段生成后必须发用户确认，确认后才生成下一段
- **时长限制**：全段 r2v（happyhorse-1.1-r2v）3–15s；脚本拆分时每段 ≤15s
- **平台偏好**：人物故事模式**优先用百炼（`MODELSTUDIO_API_KEY`）**。火山 Seedance 不支持直接上传含真人人脸的参考图/视频，传 `--ref-image` 人物图可能被拒
- **prompt 对人物明确描述**：每段都写"the same character from the reference image — keep face/hair/age/outfit EXACTLY identical"，靠参考图维持人物一致
- **角色音色跨段一致**：主角音色由「项目音色设定」中的角色条目统一规定，每段 prompt 的旁白音色描述必须逐字复用同一条，不得段间改写——人物故事里同一张脸却换了声音是硬伤
- **画面描述主焦一个明确动作**：单一动作 + 克制摄像机运动，避免同片段引入过多新道具/新人物导致穿帮
- **镜头运动要平和**：推荐 subtle slow push-in / minimal motion / static shot
- **叙事承接**：各段画面独立，prompt 文案上可承接上一段叙事，但不做首尾帧对齐
- `--ref-image` 支持本地路径（脚本自动 base64）或 `http(s)` URL

##### 模式 A.2：t2v 模式（氛围叙事类片段）

不传 `--image`，只写 prompt。适合手机底面、数据动画、产品特写等不含重要人物的场景：

```bash
python3 ./skills/video-product/scripts/gen.py \
  --prompt "画面描述：产品特写镜头，科技感背景，光影流转。音频：转场音效+悬念BGM起" \
  --ratio 9:16 --resolution 720P --duration 12 \
  --output <project-dir>/artifacts/02_xxx.mp4
```

##### 模式 A.3：r2v 模式（仅用户提供参考图时，对应 Step 3.4）

**仅当某片段用户提供了参考图**（Step 3.4 静态图片作为参考）时才走 r2v，首选 `happyhorse-1.1-r2v`（沿链 fallback），传 `--ref-image`：

```bash
python3 ./skills/video-product/scripts/gen.py \
  --prompt "参考图片中的角色/风格在 <新场景> 做 <动作>，音频：…" \
  --ref-image "<用户提供的参考图路径或URL>" \
  --ratio 9:16 --resolution 720P --duration 8 \
  --output <project-dir>/artifacts/03_xxx.mp4
```

- 百炼 r2v 首选 `happyhorse-1.1-r2v`（沿链 fallback），时长 3–15s，**仅支持 `--ref-image`**（不支持 `--ref-video`、不支持首帧 `--image`）。
- A.1 人物故事也走 r2v（同一模型），区别只在参考图来源：A.1 用生成的 `character_reference.jpg`，A.3 用用户提供的图。
- `--ref-image` 支持本地路径（脚本自动 base64）或 `http(s)` URL。

**参数说明**：
- `--prompt`：**画面+音频统一描述**。声画同出，人物对话、旁白、BGM、环境音都写在 prompt 中。
- `--ratio`：默认 `9:16`（竖屏）；`--resolution` 默认 `720P`，用户要高清用 `1080P`。
- `--duration`：按脚本片段时长，**不得超过 15 秒**（百炼 i2v/r2v 最短 3 秒）。
- `--no-audio`：用户明确不要配音时关闭声画同出。
- `--model`：显式指定模型 id，覆盖百炼按模式固定的模型。`--platform` 可覆盖自动检测。
- `--poll-interval` / `--timeout`：默认 15s / 900s，1080P 或长片段可加大 `--timeout`。

**生成后处理**：
- `gen.py` 直接把 MP4 写到 `--output`（按片段编号命名，如 `01_hook_product.mp4`），并同目录写 `<name>.json` 元数据。
- 若生成失败无音轨，后续由 Step 4.5 补 TTS。

##### 生产中常见错误与重试策略

| 错误 | 原因 | 处理 |
|------|------|------|
| `gen.py` 退出码 2 + pexels/pixabay 提示 | 两个平台 env key 都没配 | 按提示走模式 B，或 spawn IT Engineer 配置 `MODELSTUDIO_API_KEY`/`AWK_GEN_KEY` |
| HTTP 401 / API key doesn't exist | key 与平台/地域不匹配 | 检查 env 变量是否对应平台；百炼用 `MODELSTUDIO_API_KEY`，火山用 `AWK_GEN_KEY` |
| HTTP 404 / Invalid model | model id 错误 | 检查 `--model` 是否在支持列表内；火山模型须含 `doubao-` 前缀 |
| 任务 FAILED / 超时 | 渲染慢（1080P/长片段）或参数不兼容 | 百炼沿链自动 fallback（1.1→1.0→wan2.7）；仍失败则降低分辨率/缩短时长重试，或 `--model` 指定模型 |
| r2v 报错退出（传了 `--image`/`--ref-video`） | r2v 仅 `--ref-image`（happyhorse-1.1-r2v 起沿链） | r2v 不收首帧；人物故事统一用 `--ref-image`，不要传 `--image`/`--prev-segment` |
| `--output must be relative to the workspace` / `--output must be under one of: output_videos` | exec 直接调 gen.py，CWD 不在 workspace-media-operator，或 `--output` 用了绝对路径 | **exec 必须显式设 `workdir="/home/wukong/.openclaw/workspace-media-operator"`**，且 `--output` 必须是相对路径形如 `output_videos/<topic>/artifacts/NN_xxx.mp4`。gen.py 内部 `ensure_safe_output()` 强制只允许 `output_videos/` 下的相对路径，靠 `Path.cwd()` 解析根目录；同理 `compress_preview.py` 也要求相对 `--output` 在 `previews/`/`tmp/`/`output_videos/` 下，需要同样的 workdir 设置 |
| `exec denied: allowlist miss` 调 `cd <dir> && python3 ...` | `cd` 不在 allowlist（TOOLS.md 明确禁止），导致整条命令被拒 | 不要用 `cd && cmd` 包装；改用 exec 的 `workdir` 参数显式指定 CWD，命令本身用绝对路径调脚本 + 相对 `--output` |

**重试上限**：`gen.py` 内部做瞬时 HTTP 重试；百炼沿候选链自动 fallback（happyhorse-1.1 → 1.0 → wan2.7），整链都失败退出非 0 再人工重试 1 次，仍不通就告诉老板，不要 yield 死等。

#### 模式 B：Stock Footage 托底模式（gen.py 退出码 2 时）

当 `gen.py` 报"未检测到任何视频生成平台的环境变量"（退出码 2）时，回退到此模式。

**此模式下需要单独生成 TTS 配音**（见 Step 4.5），因为下载的素材无音频。

素材搜集优先级：
1. **`pexels-footage`**：从 Pexels 免费素材库搜索下载（9:16 疖屏）
2. **`pixabay-footage`**：Pexels 不可用或无结果时，从 Pixabay 下载

**素材下载规则**：
- 一次只下载一个视频
- 时长精准匹配（根据脚本片段时长设置 `--min-duration` / `--max-duration`）
- 下载后按脚本片段编号重命名

**质量自检**（仅 stock-footage 模式需要）：

```bash
python3 ./skills/video-product/scripts/check.py <project-dir>/
```

check.py 检测黑帧、分辨率、时长缺口。每下载一段素材后运行一次，直到 `verdict: "accepted"` 且时长满足。

#### Step 4.5 — TTS 配音（仅 Stock Footage 模式或 AI 生成无音频时）

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
