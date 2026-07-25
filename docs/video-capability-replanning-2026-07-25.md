# 小贝系统视频能力重新规划 — 调研与开发计划

> 起草日期：2026-07-25（周六）
> 状态：调研期（未进入开发）
> 用途：本文件用于**沉淀调研结果**与**规划出发点**，最终据此生成开发计划。开发计划不在本文件撰写，等调研结束另起一份。

---

## 0. 路线速览（本文档怎么用）

1. **第 1 节**：用户给出的规划出发点（不可改动，是后续所有调研与开发计划的约束）。
2. **第 2 节**：现状盘点（调研结果，会随调研持续追加）。
3. **第 3 节**：参考项目 MoneyPrinterTurbo 调研要点。
4. **第 4 节**：开放问题与待决项（调研中暴露、需要用户拍板的疑点）。
5. **第 5 节**：调研 todo 清单（尚待完成的事项，全部完成后再进入开发计划撰写）。

---

## 1. 规划出发点（用户钦定，调研期不得改动）

### 1.1 main agent 与 content-producer 在视频生产上的分工界限

小贝 main agent 与 content-producer 在视频生产上的职责边界如下：

| 维度 | main agent（小贝） | content-producer |
|------|------------------|------------------|
| 平台运营 | ✅ 全部负责：发送数据监控等 | ❌ 不负责 |
| 视频生产 | ⚠️ 受限 | ✅ 主力 |
| 出脚本 | ❌ 不负责 | ✅ 负责 |
| 基于已有/用户素材进行组装 | ✅ 负责 | ✅ 也可调用（基础能力） |
| 为组装目的使用 AIGC 或 **Stock Footage 模式**下载补充 | ✅ 负责 | ✅ 也可调用（基础能力） |
| 基于用户素材做简单剪辑（去口气词、高光剪辑、录制操作视频） | ✅ 负责 | ❌ 不负责（已交给 main 的 ui-demo 等） |
| 其余视频能力（含出脚本） | ❌ 不负责 | ✅ 负责 |

**核心约束**：main agent 的视频能力**仅限**以下三种场景：

1. 基于已有素材或用户给定素材进行**组装**；
2. 为上述组装目的，使用 AIGC 或 **Stock Footage 模式**进行下载补充；
3. 基于用户提供的素材进行**简单剪辑**（如去口气词、高光剪辑、录制操作视频）。

其余视频能力——包括出脚本的能力——**全部归 content-producer**。

### 1.2 技能调动已完成的部分

用户已执行下列技能调动（调研期视为现状，不要再规划调动）：

- `youtube-publish`、`bilibili-publish`、`ui-demo` 已调整至 main agent
- main agent 的 `video-produce` 技能调整到 content-producer，作为基础能力

> 调研记录：当前 `crews/content-producer/skills/video-product/SKILL.md` 仅有一行占位符（"TODO: 这里的 stages 和 scripts 作为原子能力，供 video producer 其他技能调用过程和整合"），scripts 与 stages 是从 main agent 复制过来的完整副本。这与用户描述的"调整到 content-producer 作为基础能力"一致——已迁移代码骨架，但 content-producer 侧的 SKILL.md 工作流还未撰写。

### 1.3 待后续规划的部分

- content-producer 的视频制作工作流程、约定、技能等，**后面还要再次规划**。本文件不直接撰写该流程，仅在调研 todo 里列出该调研事项。
- 目前 `crews/main/skills/video-product` 中保留的 AIGC 能力要抽到 `skills/` 中，作为公共能力同时提供给 main agent 和 content-producer。**调研期只调查抽什么、怎么抽**，实际抽取由后续开发计划执行。

### 1.4 main agent 的 video-produce 技能需要完全重构

重构思路：

- **借鉴**：https://github.com/bigbrother666sh/MoneyPrinterTurbo/tree/main（MoneyPrinterTurbo，一站式 AI 短视频生成工具）
- **保留按现有 SKILL.md**：工作区管理约定、素材补充方案、合成成品、制作封面、用户确认这些环节**按目前 SKILL.md**不改。
- **scripts 清理**：scripts 中用不到的脚本可以删除（content-producer 那里已有完整备份，删了不丢）。

> 调研记录：当前 `crews/main/skills/video-product/scripts/` 下的脚本清单为 `assemble.py / check.py / compress_preview.py / extract_and_concat.py / gen.py / review.py / state.py / tts.py`，共 8 个。重构后应保留哪些、删哪些，需要结合 MoneyPrinterTurbo 的能力拆解后才能定。

---

## 2. 现状盘点（调研结果，持续追加）

### 2.1 main agent 现有视频相关技能清单

调研日期 2026-07-25，扫 `crews/main/skills/` 下所有 SKILL.md：

| 技能 | 描述 / 用途 | 是否与本次重构相关 |
|------|------------|------------------|
| `video-product` | 当前 SKILL.md frontmatter `name: TODO:rename`，描述"将已有视频素材拼接成完整视频，支持通过 AIGC 或者 pexels-footage、pixabay-footage 进行素材补充以及按需补充配音配乐" | ✅ 本次重构的核心目标 |
| `ui-demo` | 录制产品 UI demo 视频（patchright 录屏 + 鼠标覆盖层 + 字幕），三阶段 Discover→Rehearse→Record | ✅ 已迁至 main，属于"录制操作视频"能力范畴 |
| `youtube-publish` | YouTube Data API v3 上传视频 | ⚠️ 平台运营能力，不在 video-produce 重构内但与之相关 |
| `bilibili-publish` | B 站上传 | ⚠️ 同上 |
| `viral-chaser` | 下载分析抖音/B 站/小红书爆款视频，**仅产出追爆报告**，视频生产需另行委托 content-producer | ⚠️ main 的 viral-chaser 与 content-producer 的衔接关系，重构后需重新明确 |

main agent 其余发布/运营技能（douyin-publish / wechat-channels-publish / weibo-publish / wx-mp-publisher / wx-mp-engagement / xhs-publish / xhs-content-ops / xianyu-ops / zhihu-publish / wxwork-moments 等）属平台运营范畴，按出发点 1.1 仍归 main agent，不在本次重构内。

### 2.2 content-producer 现有视频相关技能清单

扫 `crews/content-producer/skills/`：

| 技能 | 描述 / 用途 | 与本次的关系 |
|------|------------|------------|
| `video-product` | 仅占位符 SKILL.md，scripts/stages 是 main agent 的完整副本 | ✅ 出发点 1.3 明示"后面还要再次规划" |
| `siliconflow-video-gen` | SiliconFlow Video API（Wan2.2 T2V/I2V），异步提交→轮询→下载 | ✅ 可能并入公共能力 |
| `siliconflow-tts` | SiliconFlow MOSS-TTSD-v0.5 TTS | ⚠️ TTS 备选，可能并入公共能力 |
| `collage-broll` | 纸拼贴组装动画（gbro 适配版），三闸门审批，最终用 gen.py i2v 出片 | ⚠️ 高级 B-roll 能力，属 content-producer 范畴 |
| `html-video` | html-video 引擎模板驱动视频生成（23+ 模板），TTS/BGM 由 openclaw MiniMax 扩展提供 | ⚠️ 模板驱动路径，属 content-producer 范畴 |
| `manim-explainer` | Manim 科学动画 | ⚠️ 属 content-producer 范畴 |
| `design-system-picker` | 设计系统选择 | ⚠️ 属 content-producer 范畴 |
| `init-workspace` | content-producer 工作区初始化 | ⚠️ 属 content-producer 范畴 |

### 2.3 公共 skill（`skills/`）现状

扫 `skills/` 下与视频生产相关的公共技能：

| 技能 | 描述 / 用途 | 与本次的关系 |
|------|------------|------------|
| `siliconflow-img-gen` | 火山方舟 Seedream 图像生成 / 编辑（默认 doubao-seedream-4.5，fallback doubao-seedream-5.0-lite） | ✅ 出发点 1.4 提到的"制作封面"用此，已是公共能力 |
| `pexels-footage` | Pexels 版权免费图片/视频素材下载 | ✅ 出发点 1.1 提到的 Stock Footage 模式之一，已是公共能力 |
| `pixabay-footage` | Pixabay 版权免费素材下载 | ✅ 同上（未细读，但 SKILL 列表已确认存在） |
| `smart-search` / `browser-guide` / `web-form-fill` / `email-ops` / `wxwork-drive` / `complex-task` | 与视频生产无直接关系 | ❌ 不在本次范围 |

### 2.4 main agent `video-product` scripts 现状摘要

逐脚本调研（已读各脚本头部）：

| 脚本 | 行数 | 用途摘要 | MoneyPrinterTurbo 借鉴后是否仍需要 |
|------|------|---------|----------------------------------|
| `assemble.py` | 457 | 把 artifacts/ 下片段按数字前缀顺序拼接为成片；无外部音频则保留各段原音轨，有外部音频则替换 | **保留**——合成成品环节按现有 SKILL.md 不变 |
| `gen.py` | 675 | 直连百炼 happyhorse / 火山 Seedance 生成视频片段（声画同出），百炼按模式走候选链，火山走 Fast→Normal→Mini | **抽到公共 skills/**——AIGC 补充能力应公共化（出发点 1.3） |
| `tts.py` | 457 | SiliconFlow MOSS-TTSD-v0.5 TTS；与 content-producer 的 `siliconflow-tts` 脚本是同一份 | **抽到公共 skills/** 或并入 `siliconflow-tts`——避免重复 |
| `compress_preview.py` | 161 | 把视频压到 ≤16MB 用于聊天逐段确认（产物仅用于确认不参与合成） | **保留**——逐段确认是 main agent 视频生产工作流的一部分 |
| `extract_and_concat.py` | 545 | 从 MP4 抽片段（head/tail/slice）并可选拼接为一片；支持多段拼接 | **保留**——是"基于用户素材做简单剪辑"的核心脚本（出发点 1.1 第 3 条） |
| `check.py` | 472 | 检查素材质量与时长缺口（仅 Stock Footage 模式） | ⚠️ 待 MoneyPrinterTurbo 调研后定——可能保留也可能被借鉴方案替代 |
| `review.py` | 485 | 成片自检闸门：ffprobe 校验 + 4 位置抽帧黑屏扫描 + 音频电平 + 时长/分辨率一致性 | **保留**——成片自检是 main agent 交付前的强制闸门 |
| `state.py` | 184 | 项目状态机：固定阶段链 script→gate0→calibrate→assets→assemble→review→cover→deliver | ⚠️ 重构后阶段链会变（不再有 script/gate0/calibrate），脚本需重写或大幅简化 |

### 2.5 当前 SKILL.md 工作流摘要（main agent video-product）

当前 SKILL.md 描述的工作流（重构前的现状）：

1. 工作区目录准备（`output_videos/<topic-en-slug>/`，固定子目录结构 raw_materials/downloads/generations/artifacts/previews）
2. AIGC 补充生成视频片段（按需）—— 百炼 happyhorse / 火山 Seedance，含候选链 fallback
3. Stock Footage 模式（无 AIGC 可用或用户要求时）—— pexels-footage → pixabay-footage
4. 补配音配乐（用户素材需要时）—— OpenClaw 内置 TTS 优先，回退 tts.py
5. 合成成品（assemble.py）
6. 制作封面（siliconflow-img-gen，封面必须含标题文字）
7. 用户确认

**当前 SKILL.md 严重越界的地方**（按出发点 1.1 应砍掉）：

- frontmatter `description` 写的是"将已有视频素材拼接成完整视频"——OK
- 但 SKILL.md 正文里实际上**没有出脚本的环节**，而是引用了 stages/ 下的 step2-script.md（人物叙事脚本、三段式结构、声画同出音色设定、片段规划、slideshow-risk 自检、Gate 0 contact sheet、content-calibrator 打分、预算估算……）——这些都是 content-producer 范畴，**当前竟然寄生在 main agent 的 video-product 里**，是历史包袱
- 出发点 1.1 明示"出脚本的能力全部归 Content Producer"——所以重构后 SKILL.md 必须把整个 stages/ 拆掉，stages/ 在 main agent 这一侧应整体删除（content-producer 那里有完整备份）

### 2.6 viral-chaser 与 content-producer 的衔接

**已定（用户 2026-07-25 拍板）**：viral-chaser 衔接按上一轮已改的形态——viral-chaser **只管出脚本**，制作明确委托 content-producer。本节调研结束，不再作为开放问题。

> 调研差异记录：当前仓内 `crews/main/skills/viral-chaser/SKILL.md`（行 50）仍是旧措辞"仅产出追爆报告，不生成脚本，不制作视频，如需据此生成视频需另行委托 content-producer"。用户表示"上一轮已改好且已同步本地"——可能改动在别处或本地未推。此项**不在本调研范围**，仅作差异备忘，不在调研 todo 里列。

### 2.7 content-producer `video-product` 当前形态

`crews/content-producer/skills/video-product/SKILL.md`：

```markdown
TODO: 这里的stages和scripts作为原子能力，供video producer其他技能调用过程和整合
```

scripts/ 与 stages/ 是 main agent 的完整副本（含 gen.py / assemble.py / review.py / state.py / tts.py / check.py / compress_preview.py / extract_and_concat.py，以及 stages/ 下 input-sources.md / model-selection.md / prohibitions-notes.md / step2-script.md / step3-user-assets.md / step4-assets.md / step5-compose.md）。

按出发点 1.3，content-producer 侧的 SKILL.md 工作流"后面还要再次规划"——本调研文件不直接撰写该工作流，但调研 todo 里要列出该事项。

---

## 3. 参考项目 MoneyPrinterTurbo 调研要点

调研对象：https://github.com/bigbrother666sh/MoneyPrinterTurbo/tree/main（forked from harry0703/MoneyPrinterTurbo）

> ⚠️ 本节为**调研起点**，目前只抓了仓库根 README。还需进一步抓 `app/` 目录结构与关键模块源码，调研 todo 里已列出。

### 3.0 调研原则（通用，不仅针对 MoneyPrinterTurbo，后续所有项目调研都遵守）

用户 2026-07-25 钦定 3 条调研原则：

1. **UI 层面完全不看**——只吸收能力，最终落地为 openclaw 的 Skill。被调研项目的 WebUI、API controller、前端组件、CLI 交互等 UI 范式全部跳过，不调研、不借鉴。
2. **大模型/AIGC 模型的 Provider 适配层完全不看**——模型的调用适配统一按上一轮抽出的公共模块（如 `skills/aigc-video-gen/`、`skills/siliconflow-img-gen/`、`skills/siliconflow-tts/`、未来 CP 侧的 llm skill 等）。被调研项目里 `services/llm.py`、`services/voice.py` 的七条 TTS 路径、`services/material.py` 里的 Pexels/Pixabay/Coverr API key 轮转、各种 SDK 适配——**只看算法不抄适配层**。
3. **重点是看"怎么出脚本"**——尤其是像 MoneyPrinterTurbo 这种素材匹配算法（脚本 → 关键词 → 时长 → 素材挑选）。其余如视频合成技术细节、字幕烧录方式等次之。

落地约束：
- todo B 起的所有项目调研，只抓"算法/策略/工作流"层源码，绕开 controllers/、models/schema 的 API DTO、services/llm.py / voice.py 的 Provider SDK
- 调研产出回写本文档时，**只记可借鉴的能力与算法**，不抄 SDK 适配代码
- 落地成 Skill 时，调的是本仓已有公共模块，不重新引入被调研项目的 SDK 适配层

### 3.1 仓库定位

- 一站式 AI 短视频生成工具
- 用户只提供视频**主题**或**关键词**，自动生成：视频脚本 → 匹配素材 → 生成字幕和背景音乐 → 合成高清短视频
- 四种使用方式：AI Agent / WebUI / API / CLI
- 代码按控制器、服务、模型等职责分层（`app/` 目录）

### 3.2 MoneyPrinterTurbo 的能力特性（从 README 摘录）

| 能力 | MoneyPrinterTurbo 实现 | 与出发点 1.1 的契合度 |
|------|---------------------|-------------------|
| AI 自动生成视频脚本 | 内置 | ❌ 出脚本归 content-producer，main agent 借鉴时**不能照搬** |
| 自定义脚本 | 支持 | ⚠️ main agent 不出脚本但可接收用户/content-producer 给的脚本？待定 |
| 多种高清尺寸 | 竖屏 9:16 / 横屏 16:9 | ✅ 可借鉴 |
| 批量视频生成 | 一次生成多个挑最满意的 | ⚠️ 与 main agent"逐段确认"工作流冲突，是否借鉴待定 |
| 视频片段时长设置 | 可调素材切换频率 | ✅ 可借鉴 |
| 多语言视频脚本 | 支持 | ❌ 出脚本归 content-producer |
| TTS | Edge TTS / Azure Speech / SiliconFlow / Google Gemini / 小米 MiMo / ElevenLabs / Chatterbox | ✅ 可借鉴备选方案（main agent 当前 tts.py 只接 SiliconFlow） |
| 字幕生成 | 可调字体/位置/颜色/大小/描边/背景 | ⚠️ 当前 main agent assemble.py **不烧字幕**——是否引入待定 |
| 背景音乐 | 随机或指定，可调音量 | ⚠️ 当前 main agent 靠 gen.py 声画同出模型出 BGM，不单独混 BGM——是否引入待定 |
| 本地素材 / Pexels / Pixabay / Coverr | 支持四种素材来源 | ✅ Stock Footage 模式可借鉴（当前 main agent 只有 Pexels + Pixabay） |
| 跨平台发布 | TikTok / Instagram / YouTube Shorts 一键发布 | ❌ 发布归各 publish 技能，不在 video-produce 内 |
| 主流模型接入 | Kimi / Moonshot / OpenAI / Gemini / DeepSeek / 通义千问 / Azure / 火山方舟 / xAI / MiniMax / 小米 MiMo / Cloudflare AI Gateway / 魔搭 / AIHubMix 等 | ⚠️ 视频生成模型当前 main agent 只接百炼 + 火山，文本模型走 agent 本身——是否借鉴待定 |

### 3.3 待细化的 MoneyPrinterTurbo 调研项

下列项已列入调研 todo，需进一步抓 GitHub 源码：

- `app/` 目录的分层结构（controllers / services / models）
- 素材匹配的具体算法（关键词如何从脚本提炼？时长如何精准匹配？）
- 字幕生成是ffmpeg 烧录还是软字幕？
- BGM 混音的 ffmpeg 流程
- 批量生成的产物管理策略
- 它的"AI Agent"模式具体怎么调度（与 openclaw 的 subagent spawn 模式有何异同）

### 3.4 todo A 调研产出：`app/` 目录分层与关键模块（2026-07-25 完成）

clone 路径：`~/wiseflow-pro/MoneyPrinterTurbo`（参考仓统一 clone 到 `~/wiseflow-pro`，按用户约定）

`app/` 分层（FastAPI 跌架，职责清晰）：

```
app/
├── router.py            # 根 APIRouter，只 include v1 的 video/llm 两个子 router
├── config/config.py     # 配置加载（config.toml）
├── controllers/         # HTTP 接口层
│   ├── v1/
│   │   ├── video.py     # /videos POST 生成、/subtitle、/audio、/tasks、/stream、/download、/bgm、/materials
│   │   └── llm.py       # /llm/* 大模型调用接口
│   ├── manager/         # 任务队列管理：memory_manager / redis_manager（可选 Redis 后端）
│   └── ping.py
├── services/            # 业务逻辑层（本仓调研重点）
│   ├── video.py         # 视频合成主力（1372 行），走 moviepy 跌架
│   ├── material.py      # 素材搜索下载主力（479 行）：Pexels / Pixabay / Coverr，含 API key 轮转
│   ├── voice.py         # TTS 路径：Edge TTS / Azure v1+v2 / SiliconFlow / Gemini / MiMo / ElevenLabs / Chatterbox 七条
│   ├── subtitle.py      # 字幕生成：faster-whisper 本地 ASR 转写，输出 .srt
│   ├── bgm.py           # 背景音乐：支持用户上传（.mp3/.m4a/.aac/.wav/.flac/.ogg/.opus/.wma），ffmpeg 混音
│   ├── llm.py           # 脚本生成：Kimi/Moonshot/OpenAI/Gemini/DeepSeek/通义千问/Azure/火山/xAI/MiniMax/MiMo 等
│   ├── task.py / state.py / cache_manager.py / version_checker.py
│   ├── data/azure_voices.json
│   └── utils/video_effects.py
├── models/              # 数据模型层
│   ├── schema.py        # VideoParams / VideoAspect / VideoConcatMode / VideoTransitionMode / MaterialInfo 等 pydantic 模型
│   ├── const.py / exception.py / llm_provider.py
└── utils/               # 通用工具（file_security / logging_utils / utils）
```

**与出发点 1.1 的契合度复核**：

| MPT 能力 | MPT 实现位置 | 借鉴判定 |
|---------|------------|---------|
| 出脚本（LLM） | `services/llm.py` + `controllers/v1/llm.py` | ❌ 不借鉴——出脚本归 CP，main 不碰 |
| 素材匹配搜索 | `services/material.py`（Pexels/Pixabay/**Coverr**） | ✅ Stock Footage 模式可借鉴——main 当前只 Pexels+Pixabay，**Coverr 是新增素材源** |
| 视频合成 | `services/video.py`（moviepy 跌架，1372 行） | ⚠️ 与 main 当前 `assemble.py`（ffmpeg 直拼）异同：MPT 著 moviepy CompositeVideoClip，支持转场（FadeIn/FadeOut/SlideIn/SlideOut/ZoomIn/ZoomOut/Shuffle）与字幕烧录；main 当前无转场、不烧字幕。是否引入转场待 todo C 定 |
| TTS | `services/voice.py`（7 条路径） | ⚠️ main 当前 TTS 优先级"OpenClaw 内置 → siliconflow-tts"；MPT 多 6 条备选（Edge TTS/Azure/Gemini/MiMo/ElevenLabs/Chatterbox）。是否扩备选待定，但出发点明示 main 不出脚本不调 LLM，TTS 备选扩展非本轮范围 |
| 字幕生成 | `services/subtitle.py`（faster-whisper 本地 ASR） | ⚠️ MPT 字幕走 ASR 转写音频出 .srt 再烧录；main 当前 `assemble.py` **不烧字幕**。是否引入待 todo C 定 |
| BGM | `services/bgm.py`（用户上传 + ffmpeg 混音） | ⚠️ main 当前 BGM 靠 gen.py 声画同出模型一次出，不单独混。MPT 的 BGM 是独立音轨混音。是否引入待 todo C 定 |
| 批量生成 | `controllers/v1/video.py` create_task / get_all_tasks | ⚠️ MPT 一任务一产物，多任务靠 task 队列。main 当前无队列。是否引入"一次生成多个挑最满意"待 todo D 定 |

**分层借鉴结论**：MPT 的 controllers/services/models 三层分层是 FastAPI Web 服务范式，main agent 是 openclaw skill 范式（SKILL.md + scripts + wrapper），**分层结构不直接借鉴**——范式不同。借鉴的是 services 层具体能力实现（material.py 的 Coverr / video.py 的转场 / subtitle.py 的 ASR 字幕等），按需抽 idea 进 main 的 scripts。

**新增待调研项**（todo A 跑完暴露的）：

- **Coverr 素材源**：MPT 支持 Coverr 作为第三家 Stock Footage 源，main 当前只 Pexels+Pixabay。需调研 Coverr API 是否免费、是否需 key、与 Pexels/Pixabay 的素材库差异，评估是否在 main 抽公共 `coverr-footage` skill。入 todo B 范畴
- **moviepy vs ffmpeg 直拼**：MPT `video.py` 著 moviepy，main `assemble.py` 著 ffmpeg 命令拼。moviepy 抽象层更薄但依赖重（moviepy + numpy + PIL），main 当前 stdlib + ffmpeg 无第三方依赖。需调研引入 moviepy 的成本收益，入 todo C 范畴

### 3.5 todo B 调研产出：素材匹配算法与脚本生成算法（2026-07-25 完成）

按调研原则 3（重点看出脚本与素材匹配），抓 `app/services/material.py` + `app/services/llm.py` 核心算法源码。

#### 3.5.1 素材匹配算法（`material.py`）

**两套下载模式**（`download_videos` 的 `match_script_order` 开关）：

| 模式 | 开关 | 算法 | 借鉴判定 |
|------|------|------|---------|
| **随机模式**（默认） | `match_script_order=False` | 各关键词搜索结果合并大列表 → random.shuffle → 按累计时长 ≤ audio_duration 截断下载 | ⚠️ 与 main 当前 Stock Footage 流程相近（main 是逐段精准匹配，MPT 是总量截断），借鉴价值低 |
| **按脚本顺序模式** | `match_script_order=True` | `_download_videos_by_script_order`：各关键词分组存候选 → **轮询下载**（第 1 轮取每关键词第 1 候选，第 2 轮取每关键词第 2 候选…）→ 累计时长 ≤ audio_duration 截断 | ✅ **可借鉴**——保证素材顺序贴近文案顺序，避免第一个关键词吃满时间线 |

**时长匹配策略**：
- MPT：`minimum_duration=max_clip_duration`（搜素材时只保留时长 ≥ max_clip 的），下载后**按 `min(max_clip_duration, item.duration)` 累计**，超 `audio_duration` 截断
- main 当前：`--min-duration` / `--max-duration` 精准匹配，一次只下载一个
- 差异：MPT 是"软上限累计"，main 是"硬精准单次"。MPT 的累计策略对"组装模式"更友好（多段拼总时长），main 的精准策略对"单段替换"更友好。**两者不冲突，可按场景择**

**Coverr API 调研结论**（`search_videos_coverr`）：
- 端点：`GET https://api.coverr.co/videos?query=...&urls=true&sort=popular`
- 鉴权：`Authorization: Bearer <api_key>`（需 key，走 `coverr_api_keys` config）
- URL 形态：signed JWT（绑定 API key，无过期时间）——比 Pexels/Pixabay 的临时 URL 稳定
- **致命短板**：Coverr 库以 16:9 横屏为主，9:16 portrait 占比极低（约 1%），MPT 源码注释明示"不做 aspect_ratio 过滤，靠下游 resize + letterbox 统一处理"
- 借鉴判定：⚠️ main 的 video-product 默认竖屏 9:16，Coverr 的 portrait 库几乎空——**不建议抽公共 `coverr-footage` skill**，素材源仍保 Pexels+Pixabay 两家足够。Coverr 仅在用户明确要横屏 16:9 时有备选价值，可后补

#### 3.5.2 脚本生成算法（`llm.py`，按调研原则只看算法不抄 Provider 适配）

**`generate_script` 流程**：
1. `build_script_prompt` 拼系统 prompt + 运行时上下文（video_subject / paragraph_number / language / 用户额外要求）
2. 调 LLM 生成（`_generate_response`，Provider 适配层不看）
3. `format_response` 清洗：去 `*`/`#` markdown 标记、去 `[...]`/`(...)` 链接语法、按 `\n\n` 分段、取前 N 段
4. 重试 `_max_retries` 次，遇"当日额度已消耗完"文案特判报错

**`generate_terms` 关键词生成**（脚本 → 搜索关键词，这是素材匹配的入口）：
- 两套 prompt 模板（`match_script_order` 开关）：
  - **有序模式**：要求关键词按脚本叙事顺序排列（"earlier terms must describe earlier visual moments"），示例数量与 amount 强一致避免长文案少返回
  - **无序模式**：只要求关键词与主题相关，示例固定 5 个
- 约束：JSON-array of strings、每词 1-3 words、必须含视频主题、**强制英文**（"reply with english search terms only"——Stock 平台英文搜索结果更优）
- 解析：`json.loads` + 兜底正则 `\[.*\]` 抽 JSON，校验 `isinstance(list) and all(isinstance str)`

#### 3.5.3 与 main 当前 Stock Footage 流程的差异总结

| 维度 | MPT | main 当前（`crews/main/skills/video-product`） |
|------|-----|----------------------------------------------|
| 关键词来源 | LLM 从脚本生成（`generate_terms`） | ❌ main 不出脚本——按出发点 1.1，关键词由用户素材清单或 agent 直观察材需求定 |
| 素材源 | Pexels / Pixabay / Coverr 三家 | Pexels / Pixabay 两家（Coverr 横屏短板不建议加） |
| 时长匹配 | 软上限累计（`min(max_clip, item.duration)` 累加到 audio_duration） | 硬精准单次（`--min-duration`/`--max-duration` 一次一个） |
| 顺序保证 | `match_script_order` 轮询下载 | assemble.py 按文件名数字前缀排序——顺序由 agent 命名控制 |
| 下载粒度 | 批量下载到 material_directory | 一次一个（pexels-footage/pixabay-footage 强制 `--max-clips=1`） |

**借鉴结论**：
- ✅ **`_download_videos_by_script_order` 的轮询算法**可借鉴——main 的"组装模式"若需多段拼总时长，可仿此算法保证素材顺序贴近预设顺序。但 main 不出脚本，顺序由 agent 定，轮询算法的"按关键词分组"在 main 范式下退化为"按段编号分组"，实际就是当前 assemble.py 数字前缀排序的变体——**借鉴价值有限，暂不引入**
- ✅ **`generate_terms` 的 prompt 模板**（有序/无序两套 + 强制英文 + JSON-array 约束）是**出脚本范畴**，归 CP——main 不借鉴，CP 后续规划脚本生成时可参考此模板
- ❌ Coverr 不抽公共 skill（横屏短板）
- ❌ Provider 适配层、UI 层按调研原则 1/2 不看

**todo B 闭合，无新增待研项**。

### 3.6 todo C 调研产出：字幕与 BGM 流程（2026-07-25 完成）

按调研原则 1（UI 不看）2（Provider 适配不看）3（重点看出脚本与素材匹配——字幕/BGM 是次之），抓 `app/services/subtitle.py` + `app/services/bgm.py` + `app/services/video.py` 的混音调用点。

#### 3.6.1 字幕流程（`subtitle.py`）

**算法**：本地 faster-whisper ASR 转写音频 → 按词级时间戳分段（遇标点断句）→ 输出 .srt 文件

**关键参数**：
- `model_size`（默认 large-v3）、`device`（默认 cpu）、`compute_type`（默认 int8）
- `beam_size=5`、`word_timestamps=True`、`vad_filter=True`（`min_silence_duration_ms=500`）
- 模型文件落 `{root}/models/whisper-{model_size}/model.bin`，不在则走 HuggingFace 自动下载

**字幕烧录**：`subtitle.py` 只产 .srt，**烧录在 `video.py` 的 moviepy SubtitlesClip + TextClip**——属 video.py 合成范畴，不独立

**与 main 当前流程对比**：

| 维度 | MPT | main 当前 |
|------|-----|----------|
| 字幕生成 | faster-whisper 本地 ASR 转写音频出 .srt | ❌ 不烧字幕——`assemble.py` 明示"不烧字幕" |
| 字幕烧录 | moviepy SubtitlesClip + TextClip（font_name/text_color/stroke_color/stroke_width 可调） | ❌ |
| 依赖 | faster-whisper + 模型文件（large-v3 约 3GB） | 无 |

**借鉴判定**：⚠️ **不建议引入到 main**——理由三：
1. main 按出发点 1.1 不出脚本，字幕文案即脚本台词，没脚本就没"烧字幕"的输入
2. faster-whisper + large-v3 模型重（3GB），main 当前 stdlib + ffmpeg 零依赖范式会被破坏
3. main 的 video-product 走 gen.py 声画同出模型，台词由模型直接出声，无需字幕补——字幕是 CP 范畴（CP 出脚本时可决定烧不烧）

CP 后续规划若要烧字幕，可参考此算法——但 CP 也应优先走 viral-chaser 已有的火山 ASR（`VOLC_ASR_*` env 已配），不必引入 faster-whisper

#### 3.6.2 BGM 流程（`bgm.py` + `video.py` 混音点）

**BGM 来源**：用户上传（`.mp3/.m4a/.aac/.wav/.flac/.ogg/.opus/.wma`）+ 内置歌曲目录（`resource/songs/`，如 `output000.mp3`）+ 随机选择

**`should_use_bgm` 短路规则**（通用，与来源无关）：
- `bgm_type` 空或 `bgm_volume ≤ 0` → 跳过 BGM 全流程（不解析文件、不加载、不混音）
- 这一规则避免每增一个 BGM 提供商就复制一套 0 音量判断

**`resolve_bgm_file` 解析顺序**：用户上传目录 → 内置歌曲目录 → 白名单外路径拒绝（`file_security.resolve_path_within_directory` 防 path traversal）

**混音实现**（`video.py` L1227-1240，moviepy）：
1. `bgm_source_clip = AudioFileClip(bgm_file)`
2. `bgm_effects = [afx.MultiplyVolume(bgm_volume), afx.AudioFadeOut(3)]`——音量乘 + 尾 3s 渐弱
3. **若非任务层 override 传入**（即随机/自定义选的）→ `afx.AudioLoop(duration=video_clip.duration)` 循环铺满成片时长
4. `audio_clip = CompositeAudioClip([audio_clip, bgm_clip])`——与原音轨合成（无 ducking，纯叠加）

**与 main 当前流程对比**：

| 维度 | MPT | main 当前 |
|------|-----|----------|
| BGM 来源 | 用户上传 + 内置 + 随机 | gen.py 声画同出模型一次出 BGM（写在 prompt 里） |
| BGM 混音 | moviepy afx.MultiplyVolume + AudioFadeOut + AudioLoop + CompositeAudioClip | ❌ 不单独混——assemble.py 保留各段原音轨直拼 |
| 音量控制 | `bgm_volume` 可调 | ❌ 不可调（模型出的 BGM 固定） |
| 尾渐弱 | afx.AudioFadeOut(3) | ❌ |
| 循环铺满 | afx.AudioLoop | ❌（靠每段 gen.py 出的 BGM 自洽） |
| 依赖 | moviepy + numpy + PIL | 无 |

**借鉴判定**：⚠️ **不建议引入到 main**——理由三：
1. main 的 video-product 走 gen.py �声画同出，BGM 由模型按 prompt 一次出，**不需要单独混 BGM**——引入反而破坏声画同出的简洁性
2. moviepy 依赖重，与 main stdlib + ffmpeg 范式冲突
3. main 的"为组装目的 AIGC 补充"场景，BGM 已随 AIGC 片段自带；Stock Footage 场景若用户素材需要补 BGM，走 TTS + assemble.py 外部音频替换即可，不需要 moviepy 混音

CP 后续规划若要独立 BGM 轨（如 collage-broll 已有"无声交付"需求，或 html-video 已走 applySoundtrack），可参考此 `should_use_bgm` 短路规则 + AudioLoop 铺满策略——但 CP 已有 html-video 的 `applySoundtrack` 走的是另一条路，不必引入 moviepy

#### 3.6.3 todo C 闭合结论

| 项 | 借鉴到 main | 借鉴到 CP（后续规划时） |
|---|---|---|
| faster-whisper ASR 字幕 | ❌ 不引入（重依赖、main 不出脚本） | ⚠️ 可参考但应优先走已有火山 ASR |
| moviepy SubtitlesClip �烧录 | ❌ 不引入 | ⚠️ CP 已有 html-video 走 applySoundtrack，不必引入 |
| BGM should_use_bgm �路规则 | ❌ 不引入（main 声画同出不需） | ✅ 逻辑可借鉴（volume ≤ 0 短路） |
| moviepy afx 混音 | ❌ 不引入（重依赖） | ⚠️ CP 已有 applySoundtrack，不必引入 |

**无新增待研项**。todo C 闭合。

### 3.7 todo D 调研产出：批量生成策略（2026-07-25 完成）

按调研原则 1（UI 不看）跳过 `controllers/v1/video.py` 的 HTTP 接口，重点抓 `services/task.py` 的 `generate_final_videos` + `start` + `_run_pipeline` 编排算法。

#### 3.7.1 MPT 批量算法（`generate_final_videos`）

**批量机制**：靠 `VideoParams.video_count`（int）控制**同一次任务的产物数量**——`for i in range(params.video_count)` 循环调 `video.combine_videos` + `video.generate_video`，每轮产物落 `combined-{index}.mp4` / `final-{index}.mp4`

**差异产生策略**（关键）：

| 条件 | `video_concat_mode` 取值 | 差异来源 |
|------|------------------------|---------|
| `match_materials_to_script=True` | **强制 sequential** | 多产物间**无差异**——按文案顺序拼，时间线稳定可解释，所有输出等价 |
| `video_count == 1` | 沿用 `params.video_concat_mode` | 单产物，无批量差异问题 |
| `video_count > 1` 且非顺序匹配 | **强制 random** | 多产物间差异靠**素材 shuffle 打散**——每轮 `random.shuffle(downloaded_videos)` 拼不同顺序 |

**无"挑最满意"算法**：MPT **不评估、不挑选**，`video_count` 个产物全交付（WebUI/API 一并返回 `final_video_paths` 列表），由用户人眼挑。源码里无 `select_best` / `score` / `rank` 之类逻辑。

**BGM 与批量**：每轮产物独立调 `video_music_provider.generate_bgm`（若有）——多产物各自配乐，失败时该轮降级无声不浪费整任务（`warnings.append` 标记）

**任务流水线**（`start` → `_run_pipeline`）：
- `_run_pipeline` 固定阶段：script → terms → audio → subtitle → materials → final_videos → cross_post
- `start` 仅包异常兜底（`_mark_task_failed`）——无批量编排，批量靠 `video_count` 在 `generate_final_videos` 内循环

#### 3.7.2 与 main 当前流程对比

| 维度 | MPT | main 当前 |
|------|-----|----------|
| 批量触发 | `params.video_count` | ❌ 无——一次一产物 |
| 差异产生 | 素材 random shuffle（多产物） | ❌ |
| 顺序匹配批量 | `match_materials_to_script` 时强制 sequential，多产物等价 | ❌ |
| 评估挑选 | ❌ 不挑，全交付用户人眼定 | ❌——单产物无需挑 |
| 产物管理 | `combined-{i}.mp4` + `final-{i}.mp4` 落 task_dir | `output_videos/<slug>/video.mp4` 单文件 |

#### 3.7.3 借鉴判定

**⚠️ 不建议引入到 main**——理由四：

1. **main 不出脚本**——MPT 的批量差异靠"同脚本不同素材顺序"，main 没脚本就没了批量的意义前提。main 的"组装"是用户给定素材清单，顺序由 agent 定，shuffle 反而破坏用户意图
2. **main 走逐段确认**——`compress_preview.py` + SKILL.md 明示"逐段发用户确认"，单产物已是慢流程；批量 N 产物会把每段确认膨胀 N 倍，用户体验崩
3. **声画同出模型无批量差异**——main 的 gen.py 走百炼/火山声画同出，同 prompt 同 seed 出同产物，批量要靠 prompt/shuffle 变；MPT 的素材 shuffle 范式不适用 gen.py 声画同出
4. **"挑最满意"在 main 范式下退化为 review.py**——main 已有 `review.py` 成片自检闸门（ffprobe + 抽帧黑屏扫描 + 音频电平 + 时长分辨率一致性），verdict pass/fail/warn，**这已是"挑"的逻辑**——不及格的修或重，及格的交付。引入"多产物挑最满意"无增量价值

**借鉴结论**：
- ❌ `video_count` 批量机制不引入 main——与逐段确认 + 声画同出 + review.py 范式冲突
- ❌ random shuffle 差异产生不引入——破坏用户素材顺序意图
- ✅ **`_run_pipeline` 的固定阶段链思路可参考**——main 重构时若重写 state.py（已定 4.5 删），可仿此"script→terms→audio→...→final"的阶段定义写 SKILL.md 工作流文（仅参考思路，不抄代码，也不上脚本化状态机——4.5 已定 main 用不上 state.py）

**无新增待研项**。todo D 闭合。

### 3.8 todo E 调研产出：content-producer 已有视频技能全景（2026-07-25 完成）

按调研原则 1（UI 不看）2（Provider 适配不看），把 CP 侧 collage-broll / html-video / manim-explainer / design-system-picker / init-workspace 五个 SKILL.md 全读完，理清 CP 侧已有视频生产路径，避免重构后两边重复。

> collage-broll 与 html-video 的 SKILL.md 在 todo A 阶段已细读（见 2.2 节清单），本节直接引用结论不重读。

#### 3.8.1 CP 侧五技能职责矩阵

| 技能 | 职责定位 | 视频生产路径 | 与 main 重构的重复风险 |
|------|---------|------------|---------------------|
| `collage-broll` | 把一句 ~5s 口播压成 editorial 纸拼贴组装动画（gbro 适配版） | Gate1 隐喻 → Gate2 siliconflow-img-gen 静帧 → Gate3 调公共 `aigc-video-gen` i2v 首尾帧插值出 5s 720x1280 无声/带声 MP4 | ❌ 无重复——属 CP 高级 B-roll，main 不做拼贴动画 |
| `html-video` | html-video 引擎模板驱动视频（23+ 模板，Content-Graph IR） | content-graph.json → 素材预获取（用户预置/video_generate/siliconflow-video-gen/pixabay/pexels）→ project-set-var 注入 → MiniMax TTS+BGM → hv.sh project-render | ⚠️ 素材预获取链与 main Stock Footage 重叠，但 html-video 是模板渲染范式，main 是 ffmpeg 直拼范式，**范式不同不重复** |
| `manim-explainer` | Manim 技术 explainer 动画（图/流程/架构/指标） | 定义视觉论点 → 拆 3–6 场 → 写 Manim 代码 → render-manim.sh 三档质量（low/medium/high）渲染 → 可 hand off 给 fragment-assembly + siliconflow-tts | ❌ 无重复——Manim 是科学动画，main 不做 |
| `design-system-picker` | 从内置 14 套设计系统库匹配风格规范（Stripe/Vercel/Linear/Notion/Apple/Supabase/Shopify/Figma/Spotify/Tesla/Framer/Airbnb/BMW/IBM/Starbucks） | `pick.sh "<风格描述>"` → 匹配 → 读 `./design-systems/<name>.md` 8 段规范（Visual Theme/Color/Typography/Components/Layout/Depth/Do's&Don'ts/Responsive） | ❌ 无重复——这是设计规范选择，不是视频生产，main 不做设计 |
| `init-workspace` | 为单项设计任务创建标准目录 + brief 模板 | `init.sh <任务名>` → `design_assets/YYYY-MM-DD-<任务名>/{brief.md,prompts.json,source/,output/}` | ⚠️ 与 main 的 `output_videos/<topic-en-slug>/` 工作区约定不同目录——**各自范式自洽，不强行统一** |

#### 3.8.2 CP 侧视频生产的三条平行路径

CP 侧已有视频生产不是一条链，是**三条平行路径**，按内容类型择：

1. **拼贴动画路径**（collage-broll）：口播文稿 → 纸拼贴组装动画，走 Gate1/2/3 三闸门，最终调公共 `aigc-video-gen` i2v 出片
2. **模板驱动路径**（html-video）：Content-Graph IR → 23+ 模板 → hv.sh 渲染，TTS/BGM 走 MiniMax 扩展
3. **科学动画路径**（manim-explainer）：Manim 代码 → render-manim.sh 三档渲染，可 hand off 给 fragment-assembly + siliconflow-tts

**三条路径的共同基础设施**：
- 视频生成：公共 `aigc-video-gen`（本轮已抽，collage-broll Gate3 已改调）+ CP 专属 `siliconflow-video-gen`（Wan2.2，html-video 素材预获取链用）
- TTS：公共 `siliconflow-tts`（本轮已抽，优先 OpenClaw 内置 → 本脚本回退）+ MiniMax 扩展（html-video 走的）
- 图像：公共 `siliconflow-img-gen`（collage-broll Gate2 / 封面）
- 素材：公共 `pexels-footage` / `pixabay-footage`（html-video 素材预获取链兜底）
- 设计规范：CP 专属 `design-system-picker`（设计任务前调）
- 工作区初始化：CP 专属 `init-workspace`（设计任务前调，落 `design_assets/`）

#### 3.8.3 与 main 重构的重复风险复核

| 维度 | main 重构后 | CP 现状 | 重复？ | 处置 |
|------|------------|---------|-------|------|
| 视频生成 AIGC | 公共 `aigc-video-gen` | 公共 `aigc-video-gen`（collage-broll Gate3）+ CP `siliconflow-video-gen` | ✅ 公共部分共享，不重复；CP 专属 siliconflow-video-gen 是另一家平台不合并 | 已落地 |
| TTS | 公共 `siliconflow-tts` | 公共 `siliconflow-tts` + MiniMax 扩展 | ✅ 公共部分共享，不重复；CP MiniMax 是另一条 TTS 路属 CP 范畴 | 已落地 |
| Stock Footage | 公共 `pexels-footage` / `pixabay-footage` | 同 | ✅ 完全共享，不重复 | 已落地 |
| 图像/封面 | 公共 `siliconflow-img-gen` | 同 | ✅ 完全共享，不重复 | 已是公共 |
| 工作区约定 | `output_videos/<topic-en-slug>/` | `design_assets/YYYY-MM-DD-<task>/`（init-workspace）+ `output_videos/<slug>/`（collage-broll 沿 xiaobei 路径契约） | ⚠️ CP 内部两套目录并存——设计任务走 design_assets，视频任务走 output_videos | **不强行统一**——main 用 output_videos，CP 视频也用 output_videos（collage-broll 已如此），CP 设计用 design_assets，各自自洽 |
| 简单剪辑 | main 专属 `extract_and_concat.py` + 去口气词 + 高光剪辑（待写） | CP 无 | ❌ 无重复——CP 不做基于已有素材的轻剪辑 | 已定 4.4 |
| 脚本生成 | main 不出脚本 | CP 范畴（待后续规划） | ❌ 无重复 | 已定 4.1 |

#### 3.8.4 todo E 闭合结论

- ✅ CP 侧五技能职责已理清，三条平行视频生产路径定位完成
- ✅ 与 main 重构的重复风险复核：**公共基础设施已共享**（aigc-video-gen / siliconflow-tts / siliconflow-img-gen / pexels-footage / pixabay-footage），**无新重复**
- ⚠️ CP 侧 `video-product` SKILL.md 仍占位符（出发点 1.3 "后面还要再次规划"）——本轮不动，等 CP 工作流规划时据本节全景图撰写
- ⚠️ CP 侧 `siliconflow-video-gen`（Wan2.2）保留不合并——与公共 `aigc-video-gen`（百炼+火山）是两家不同平台，CP 范式自洽

**无新增待研项**。todo E 闭合。

### 3.9 todo F 调研产出：公共 skills 命名约定（2026-07-25 完成）

扫 `skills/` 下 13 个公共 skill（含本轮新抽的 aigc-video-gen / siliconflow-tts）的命名风格，定公共命名约定。

#### 3.9.1 现有命名风格分布

| 命名格式 | 数量 | 例子 | 选用场景 |
|---------|------|------|---------|
| **平台-能力**（platform-capability） | 6 | `pexels-footage` / `pixabay-footage` / `siliconflow-img-gen` / `siliconflow-tts` / `wxwork-drive` / `email-ops` | 脚本绑某家外部平台 API（SiliconFlow / Pexels / Pixabay / 微信工作台 / Email）——命名直接反映"调哪家 API" |
| **能力**（capability） | 7 | `browser-guide` / `complex-task` / `smart-search` / `web-form-fill` / **`aigc-video-gen`**（本轮新抽） | 脚本跨多家平台 fallback 或不绑外部平台——命名反映"做什么"而非"调哪家" |

#### 3.9.2 公共命名约定（成文）

用户 4.2 拍板"命名自定"后，本轮据现状抽出约定：

1. **脚本绑单一外部平台 API** → 用 **平台-能力** 格式（`<platform>-<capability>`）
   - 例：`pexels-footage`（只调 Pexels）、`siliconflow-img-gen`（只调火山方舟 Seedream，虽是"火山"但沿用 SiliconFlow 旧名兼容）
   - 落 wrapper 名 `<skill>.sh` 与目录名一致

2. **脚本跨多家平台 fallback 或不绑外部平台** → 用 **能力** 格式（`<capability>` 或 `<capability>-<noun>`）
   - 例：`aigc-video-gen`（百炼 happyhorse + 火山 Seedance 嫦选链 fallback，不绑单一平台）、`browser-guide`（浏览器操作指南无平台 API）
   - 不强行加平台前缀——`aigc-video-gen` 不叫 `dashscope-video-gen` 也不叫 `volcengine-video-gen`，因为脚本内含双平台 fallback，绑名会误导

3. **新增公共 skill 时**：
   - 先判断脚本是否绑单一外部平台——是 → 平台-能力；否 → 能力
   - wrapper 名 = 目录名 = SKILL.md frontmatter `name`，三者强一致
   - 软链到 `~/.openclaw/bin/` 后走 PATH 调用，agent 零路径拼接

#### 3.9.3 本轮已抽公共 skill 命名复核

| skill | 命名格式 | 落地 | 复核结论 |
|------|---------|------|---------|
| `aigc-video-gen` | 能力（跨平台 fallback） | ✅ 本轮新抽，脚本含百炼+火山双平台 fallback——用能力格式不绑平台，与约定 2 一致 | ✅ |
| `siliconflow-tts` | 平台-能力（绑 SiliconFlow API） | ✅ CP 侧上移成公共，脚本只调 SiliconFlow MOSS-TTSD——用平台-能力，与约定 1 一致 | ✅ |

#### 3.9.4 todo F 闭合结论

- ✅ 公共 skills 命名约定已成文（约定 1/2/3）
- ✅ 本轮新抽的 aigc-video-gen / siliconflow-tts 命名复核通过
- 后续新增公共 skill 据此约定命名，不需再调研

**无新增待研项**。todo F 闭合。

### 3.10 todo G 调研产出：ui-demo 与 video-product 重构后的衔接（2026-07-25 完成）

调研 ui-demo 录制产物格式与 video-product `assemble.py` 的兼容性，判断是否需要在 ui-demo 后加转码步骤。

#### 3.10.1 ui-demo 产物格式

| 录制路径 | 输出格式 | 分辨率 | 编码 |
|---------|---------|--------|------|
| patchright `recordVideo`（手动注入方案） | **WebM**（`demo-FEATURE.webm`） | 1280x720（16:9 横屏） | VP8/VP9 + Opus/Vorbis（patchright/Chromium 默认） |
| patchright `screencast.start`（1.60+ Screencast API 方案） | **WebM** | 同上 | 同上 |

两种录制路径均出 WebM，**ui-demo 不产 MP4**。

#### 3.10.2 assemble.py 的 WebM 兼容性

`assemble.py` L30：`VIDEO_EXTS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}`——**`.webm` 已在支持列表**，assemble.py 扫 artifacts/ 时会识别 WebM 文件。

**normalize 阶段内置转码**（L167-211）：
- 每段视频单独 `ffmpeg -i <vf> -vf <vf_filter> ...` normalize——ffmpeg 原生能解 WebM（VP8/VP9 + Opus/Vorbis），normalize 后产 `norm_*.mp4`（libx264 + aac）
- 即 **WebM → MP4 转码已在 normalize 阶段自动完成**，拼后产物是标准 MP4，无需外置转码步骤

#### 3.10.3 衔接结论

| 维度 | 结论 |
|------|------|
| 格式兼容 | ✅ ui-demo 的 WebM 直接丢 `artifacts/` 即可被 assemble.py 识别与处理 |
| 转码步骤 | ❌ **不需要在 ui-demo 后加外置转码**——assemble.py normalize 阶段已内置 WebM→MP4 |
| 分辨率匹配 | ⚠️ ui-demo 默认 1280x720（16:9 横屏），video-product 默认 9:16 竖屏——assemble.py 的 `pad` 滤镜会按目标 width/height 信箱化（letterbox），不裁切不变形；但若 ui-demo 片段与其他段比例差异大，成片会现黑边。**这是 agent 命名与素材选择时要注意的，不是脚本缺陷** |
| 音轨 | ui-demo 录制含系统音 + 注入字幕条无音轨——assemble.py "无外部音频时保留各段原音轨"逻辑会保留 ui-demo 的系统音；若需替换为 TTS 旁白，走"有外部音频文件"路径（`speech.mp3`） |

#### 3.10.4 重构后衔接工作流（建议）

ui-demo 录制完毕后，agent 直接：
1. 把 `demo-FEATURE.webm` 拷到 `<project-dir>/artifacts/<NN>_<label>.webm`（按段编号命名，与 assemble.py 数字前缀排序约定一致）
2. 进 video-product 的合成环节，assemble.py 自动 normalize + 拼接
3. **无需任何转码中间步骤**——与"基于用户素材进行组装"的出发点 1.1 第 1 条完全契合

#### 3.10.5 todo G 闭合结论

- ✅ ui-demo WebM 产物与 assemble.py 兼容性已确认——`.webm` 在 `VIDEO_EXTS`，normalize 阶段内置转码
- ✅ 不需要在 ui-demo 后加外置转码步骤
- ⚠️ 分辨率差异（16:9 vs 9:16）靠 assemble.py pad 信箱化处理，agent 选素材时注意比例搭配即可
- 重构后 SKILL.md 工作流文应明示"ui-demo 产物可直接进 artifacts/，无需转码"

**无新增待研项**。todo G 闭合。

### 3.11 todo H 调研产出：去口气词与高光剪辑的实现方式（2026-07-25 完成）

按调研原则 1（UI 不看）2（Provider 适配不看——ASR 统一走 viral-chaser 已配的火山方舟豆包语音极速版 `volc.bigasr.auc_turbo`，不引入 faster-whisper / whisper.cpp / Silero VAD 等新依赖），调研去口气词与高光剪辑的实现方式。

#### 3.11.1 开源项目调研结论

web 查到 5 个去口气词/高光剪辑开源项目，按"是否可移植到 main 当前范式（stdlib + ffmpeg，无重依赖）"筛：

| 项目 | 实现路径 | 依赖 | 移植判定 |
|------|---------|------|---------|
| **trsdn/autocut** | ASR（Parakeet/whisper.cpp）→ silencedetect + filler regex + LLM redundancy → cut_plan.json → ffmpeg render；broadcast 音频链（EBU R128 −16 LUFS） | FluidAudio CLI / NeMo Parakeet / whisper.cpp | ❌ 不移植——依赖三个 ASR 后端，main 已有火山 ASR 不重复 |
| **MistyChen999/video-clean-cut** | auto-editor 去停顿 + faster-whisper 字级时间戳 + Pillow 字幕标题 + FFmpeg 合成；**中文优先**，去语气词（嗯/呃/额/唔/哎/诶/欸） | auto-editor + faster-whisper + Pillow | ⚠️ 中文语气词清单可借鉴，依赖不移植 |
| **timkulbaev/ai-video-editor** | Silero VAD + faster-whisper large-v3 + FFmpeg；filler words en/ru 列表 + restart detection（"cut cut"标记）+ repeated sentence detection | Silero VAD + faster-whisper + OpenRouter LLM（可选） | ⚠️ restart detection 思路可借鉴（高光剪辑场景"剪掉重录的失败段"），依赖不移植 |
| **LYK-love/autocut** | ASR（Whisper/faster-whisper/SenseVoiceSmall/Qwen3-ASR）→ .srt + .md 选择文件 → 人工勾选保留句 → 按时间戳剪 | 多 ASR 后端 | ❌ 不移植——人工勾选范式与 agent 自动剪辑冲突 |
| **qkirara/Smart-Cut** | faster-whisper word timestamps → 多层检测（silence/repeats/fillers/stutters/false starts/orphan fragments）→ 两遍 ffmpeg 关键帧对齐剪切；中文优先 | faster-whisper + LLM（可选） | ✅ **多层检测算法可借鉴**——fillers/stutters/false starts/orphan fragments 五类检测的判据与阈值 |

**共同范式提炼**（5 个项目的公约数）：
1. 抽音频 16kHz mono WAV（ffmpeg `-vn -ar 16000 -ac 1 -f wav`）
2. ASR 转写拿**字级时间戳**（word-level timestamps，非 utterance 级）——这是精确定位口气词的前提
3. 检测多类要剪的段：silence（静音）、fillers（语气词）、stutters（结巴）、false starts（重起头）、orphan fragments（孤立短碎片）、repeats（重复句）
4. 生 cut_plan.json（每段 keep/remove + 起止时间，auditable）
5. ffmpeg 按计划剪切 + 拼接 + 40ms fades 防咔点

#### 3.11.2 viral-chaser 火山 ASR 复用可行性

viral-chaser 的 `transcriber.ts` 已调火山方舟豆包语音·录音文件极速版（`volc.bigasr.auc_turbo`），原生返回 **utterance 级**时间戳（`start_time`/`end_time`，毫秒）+ **word 级时间戳**——见 transcriber.ts 注释明示"原生返回 utterances 带 start_time/end_time（毫秒）和 word 级时间戳"。

**复用可行性**：
- ✅ env 已配（`VOLC_ASR_APP_ID` + `VOLC_ASR_ACCESS_KEY` 或 `VOLC_ASR_APP_KEY`），main agent 调即用
- ✅ word 级时间戳支持——精确定位"嗯/呃/额"等单字语气词
- ✅ 16kHz mono WAV 输入约定与 viral-chaser 一致（audio_extractor.ts 同参数）
- ⚠️ 火山 ASR 是云 API（按次/按时长计费），非本地 faster-whisper——但 main 已无本地 ASR 依赖，复用云 ASR 不增新依赖，反而更轻
- ⚠️ 火山 ASR 返回 JSON 结构与 faster-whisper 不同——脚本需按火山 schema 解析（transcriber.ts 已有 Python 解析逻辑可抄）

#### 3.11.3 移植/自写成本评估

| 方案 | 成本 | 优劣 |
|------|------|------|
| 整体移植 trsdn/autocut | ❌ 高——三 ASR 后端 + FluidAudio CLI bootstrap，与 main stdlib 范式冲突 | 不推荐 |
| 整体移植 video-clean-cut | ⚠️ 中——auto-editor 二进制 + faster-whisper + Pillow，破坏 main 范式 | 不推荐 |
| **自写：火山 ASR + 多层检测 + ffmpeg 剪拼** | ✅ **低**——复用 viral-chaser 火山 ASR 调用代码 + 抄 Smart-Cut 的多层检测判据 + stdlib ffmpeg 剪拼（assemble.py 同范式） | **推荐** |
| 仅借鉴语气词清单 | ✅ 极低——抄 video-clean-cut 的"嗯/呃/额/唔/哎/诶/欸"列表 | 必抄 |

**结论**：**自写**，不移植整包。脚本走"火山 ASR 转写 → 多层检测生 cut_plan.json → ffmpeg 剪拼"路径，与 main 当前 `extract_and_concat.py` + `assemble.py` 范式一致，不引入新依赖。

#### 3.11.4 脚本骨架草案（**抽独立技能，不入 video-assembler**）

> **2026-07-25 修正**：原结论是脚本落 `crews/main/skills/video-product/scripts/`（重构后 video-assembler），用户回拍明确**去口气词与高光剪辑是单独的两个技能，跟 video-assembler 完全没有关系**——本节脚本草案改入独立技能（命名待开发计划定，候选 `filler-cut` + `highlight-cut`，或合一名 `smart-cut`），不胉 video-assembler。

新建独立技能目录下两脚本（`crews/main/skills/<独立技能名>/scripts/`）：

**1. `cut_plan.py` — 检测生计划**

```python
#!/usr/bin/env python3
"""去口气词/高光剪辑 — 检测生 cut_plan.json。

用法：
  python3 cut_plan.py <input.mp4> [--mode filler|highlight|both] [--language zh|en]

流程：
  1. ffmpeg 抽 16kHz mono WAV
  2. 调火山 ASR（复用 viral-chaser transcriber.ts 的 Python 解析逻辑）拿 word 级时间戳
  3. 多层检测：
     - fillers：语气词清单匹配（嗯/呃/额/唔/哎/诶/欸 + en: um/uh/uhm）
     - silence：word gap > 0.6s（可调 --silence-gap）
     - stutters：单字重复 ≥ 4 次（如"我我我我"）
     - false_starts：短句（< 0.3s）后接同义长句
     - repeats：句级文本相似度 > 0.6（Levenshtein/Jaccard）
  4. 输出 cut_plan.json：[{keep: bool, start: float, end: float, reason: "filler"/"silence"/...}]

依赖：火山 ASR env（VOLC_ASR_*）+ ffmpeg/ffprobe；无第三方 Python 包。
"""
```

**2. `apply_cut.py` — 按计划剪拼**

```python
#!/usr/bin/env python3
"""按 cut_plan.json 剪拼视频。

用法：
  python3 apply_cut.py <input.mp4> <cut_plan.json> [--output output.mp4] [--fade-ms 40]

流程：
  1. 读 cut_plan.json，滤 keep=true 段
  2. ffmpeg atrim/ss 逐段抽出（关键帧对齐两遍法：第一遍抽粗段，第二遍精定位）
  3. 段间加 40ms triangular fade 防咔点
  4. concat 拼接 + libx264/aac 编码

依赖：ffmpeg；无第三方 Python 包。与 extract_and_concat.py 同范式。
"""
```

**与 video-assembler 的 `extract_and_concat.py` 分工**：
- `extract_and_concat.py`（video-assembler 内）：**人工指定**剪头/尾/中段 + 拼接（用户告诉 agent 剪哪）
- `cut_plan.py` + `apply_cut.py`（独立技能）：**自动检测**剪哪（agent 跑脚本自判，用户只给源视频 + 模式开关）

**高光剪辑的特化**：
- `--mode highlight` 时，cut_plan.py 的检测策略反过来——不剪 fillers/silence，而是**识别高光段**（语音密度高 + 语速快 + 关键词命中 + 与全片文本相似度低的"新颖段"），keep 只保留高光段，其余 remove
- 高光判据待开发计划阶段细化（参考 Smart-Cut 的"intra-segment restart detection"反过来用——restart 段是低光，非 restart 段是常规，特别密的非常规段是高光）

#### 3.11.5 todo H 闭合结论

- ✅ 5 个开源项目调研完，整体移植不推荐（依赖重破坏 main 范式）
- ✅ viral-chaser 火山 ASR 复用可行性确认——word 级时间戳 + env 已配
- ✅ 自写方案落：`cut_plan.py`（检测）+ `apply_cut.py`（剪拼），stdlib + ffmpeg 范式
- ✅ 脚本骨架草案入 3.11.4 节，开发计划阶段据此细化
- ⚠️ 高光剪辑的"高光判据"待开发计划阶段细化（本节只定方向：语音密度 + 语速 + 关键词 + 新颖度）
- **2026-07-25 修正**：去口气词与高光剪辑抽**独立技能**（命名待开发计划定），**不胉 video-assembler**——与 video-assembler 完全脱钩，video-assembler 只管"基于已有素材组装"，不做自动检测剪辑

**无新增待研项**。todo H 闭合。

### 3.12 todo I 调研产出：scripts 依赖图与删除清单（2026-07-25 完成）

按出发点 1.4（"scripts 中用不到的脚本可以删除，content-producer 那里已有完整备份"），扫 main agent `crews/main/skills/video-product/scripts/` 现状 + SKILL.md 引用 + 脚本间互调，定删除清单。

#### 3.12.1 现状清单（本轮抽公共后）

本轮抽公共已删 `gen.py` + `tts.py`，剩 6 个脚本：

| 脚本 | 行数 | 用途 | SKILL.md 引用 | 脚本间互调 |
|------|------|------|-------------|----------|
| `assemble.py` | 457 | 片段按数字前缀拼成片 | ✅ 6 处（合成成品节 + 脚本清单） | ❌ 无 |
| `compress_preview.py` | 161 | 压视频 ≤16MB 用于聊天逐段确认 | ✅ 1 处（脚本清单） | ❌ 无 |
| `extract_and_concat.py` | 545 | 抽头/尾/中段 + 拼接（基础剪辑） | ❌ SKILL.md 未引用（重构后该写） | ❌ 无 |
| `check.py` | 472 | 素材质量 + 时长缺口自检（仅 Stock Footage 模式） | ✅ 1 处（脚本清单） | ❌ 无 |
| `review.py` | 485 | 成片自检闸门（ffprobe + 抽帧 + 音频电平 + 时长分辨率一致性） | ❌ SKILL.md 未引用（重构后该写） | ❌ 无 |
| `state.py` | 184 | 项目状态机（script→gate0→calibrate→assets→assemble→review→cover→deliver） | ❌ SKILL.md 未引用 | ❌ 无 |

**脚本间互调**：grep `import (assemble|check|...)` + `subprocess.*\.py` 均无命中——6 个脚本全是**独立工具脚本**，无相互依赖，删除任一个不影响其他。

#### 3.12.2 删除清单（出发点 1.4）

| 脚本 | 判定 | 理由 |
|------|------|------|
| `state.py` | ❌ **删除** | 决策 4.5 已定"main agent 用不上"——不出脚本/不走 Gate 0/不打分定稿，前三段不存在；后五段靠 SKILL.md 工作流文表述，不上脚本化状态机。CP 侧有完整备份兜底 |
| `check.py` | ⚠️ **待定，倾向保留** | "仅 Stock Footage 模式"自检——按出发点 1.1 main 仍可用 Stock Footage 补素材，check.py 的时长缺口检测在 Stock Footage 流程里有用。但 MoneyPrinterTurbo todo B 调研结论是 MPT 不做这种自检（MPT 走软上限累计），且 main 的 pexels-footage/pixabay-footage 已强制 `--max-clips=1` + 精准 `--min-duration`/`--max-duration`，素材时长缺口在下载时即被卡——**check.py 的"事后自检"在 main 范式下前置化了，事后自检冗余**。最终判定待开发计划阶段结合重构后工作流定 |
| `assemble.py` | ✅ **保留** | 合成成品环节按现有 SKILL.md 不改（出发点 1.4 明示） |
| `compress_preview.py` | ✅ **保留** | 逐段确认是 main 工作流的一部分 |
| `extract_and_concat.py` | ✅ **保留** | "基于用户素材做简单剪辑"的核心脚本（出发点 1.1 第 3 条） |
| `review.py` | ✅ **保留** | 成片自检是交付前强制闸门（SKILL.md 明示"必须先过 review.py"） |

#### 3.12.3 重构后 scripts 目录预期（开发计划阶段落地）

```
crews/main/skills/<新技能名>/scripts/
├── assemble.py            # 保留——合成成品
├── compress_preview.py    # 保留——逐段确认
├── extract_and_concat.py  # 保留——基础剪辑
├── review.py              # 保留——成片自检闸门
├── cut_plan.py            # 新增——去口气词/高光剪辑检测生计划（todo H 骨架）
├── apply_cut.py           # 新增——按计划剪拼（todo H 骨架）
└── （check.py 待定）
```

**已删**：`gen.py`（抽公共 `aigc-video-gen`）、`tts.py`（抽公共 `siliconflow-tts`）、`state.py`（决策 4.5）

**SKILL.md 重构后该补的引用**：
- `extract_and_concat.py`——当前 SKILL.md 未引用，重构后"简单剪辑"节要写调用范例
- `review.py`——当前 SKILL.md 未引用，重构后"成片自检"节要写强制闸门调用
- `cut_plan.py` + `apply_cut.py`——新增的"去口气词/高光剪辑"节要写

#### 3.12.4 todo I 闭合结论

- ✅ 6 个脚本依赖图理清——全独立工具脚本无互调，删任一不影响其他
- ✅ 删除清单定：`state.py` 删（决策 4.5），`check.py` 倾向保留但最终待开发计划定
- ✅ 重构后 scripts 目录预期产出，新增脚本（cut_plan/apply_cut）入清单
- SKILL.md 重构后该补的引用点已列出

**无新增待研项**。todo I 闭合。

---

## 4. 开放问题与待决项（调研中暴露、需要用户拍板的疑点）

> 这一节是调研过程中暴露的、不在出发点里明示、需要用户决策的疑点。**等调研 todo 全部完成后，统一发起 `request_user_input` 一次性问清**，避免逐条打断。

### 4.1 main agent video-produce 重构后接受"脚本"的边界

**已定（用户 2026-07-25 拍板）**：main agent **不接受任何脚本输入**。出脚本/探讨脚本一律走 content-producer，main agent 顶多在 viral-chaser 之后把活儿转给 content-producer。用户有脚本或需要探讨脚本 → 直接找 content-producer，不经过 main agent。

**落地约束**：
- 重构后 SKILL.md 的输入接口**只接受素材清单**（用户给定的素材、已有素材、或为组装目的经 AIGC/Stock Footage 补的素材），**不接受 script.md 类形态**
- viral-chaser → content-producer 的衔法保持上一轮已改形态，main agent 不在中转脚本
- "脚本规划表"那种东西在 main agent 侧不该出现，重构时连带把寄生在 stages/ 下的 step2-script.md 等砍干净（参见 2.5 节）

### 4.2 AIGC 抽到公共 skills 的命名与边界

**已定（用户 2026-07-25 拍板："你看着起吧"）**：命名由我方自定，按 `skills/` 现有"平台-能力"风格（pexels-footage / pixabay-footage / siliconflow-img-gen）起名。调研 todo F 由此变为"自定命名后备案"，不再作为开放问题阻塞。

落地约定（我方拟）：
- 抽公共的 AIGC 视频生成 skill 命名为 **`aigc-video-gen`**（不绑平台——脚本内含百炼+火山双平台 fallback，绑平台名会误导）
- 与 content-producer 已有 `siliconflow-video-gen` 的关系：`siliconflow-video-gen` 是 CP 侧接 SiliconFlow Wan2.2 的独立实现，调的是另一条 API、另一家平台，**不复用不合并**，保留 CP 侧原样；公共 `aigc-video-gen` 只抽 main agent 当前 `gen.py`（百炼 happyhorse + 火山 Seedance 候选链）

### 4.3 TTS 重复实现去重

**已定（用户 2026-07-25 拍板）**：main agent 的 `scripts/tts.py` 与 content-producer 的 `siliconflow-tts/scripts/tts.py` 是同一份代码——合并抽到公共 `skills/`，并在技能文档里强制写明：

> **优先使用 OpenClaw 内置 TTS 工具**（`tts_generate` 或 agent 内置语音合成能力）。
> OpenClaw 内置 TTS 不可用时，回退到本地脚本（要求环境变量已经配置 `SILICONFLOW_API_KEY`）。

落地约定：
- 公共 skill 命名沿用 **`siliconflow-tts`**（与 CP 侧现名一致，减迁移成本）
- main agent 的 `crews/main/skills/video-product/scripts/tts.py` 删除，改调公共
- CP 的 `crews/content-producer/skills/siliconflow-tts/` 整目录上移到 `skills/siliconflow-tts/`，CP 侧改用公共引用

### 4.4 简单剪辑能力的脚本归属

出发点 1.1 第 3 条提到 main agent 可做"去口气词、高光剪辑、录制操作视频"。

- 已有 `extract_and_concat.py`（剪头/尾/中段+拼接）✅ 覆盖了基础剪辑
- 已有 `ui-demo` 技能 ✅ 覆盖了"录制操作视频"

**已定（用户 2026-07-25 拍板）**："去口气词"与"高光剪辑"都归 **main agent**——它们都属于"用户提供素材后的轻剪辑"，main agent 直接做，**不外发** content-producer。content-producer 主要负责"从头生产一整个工作（视频、视觉等）"，这类基于已有素材的轻剪辑不在 CP 职责里。

**落地约束**：
- 这两项能力属本次重构范围内（不是只调研），开发计划里须列脚本/能力产出项
- "去口气词"——需 ASR（语音转写）+ 口语词检测 + 精定位 + 删除。viral-chaser 已有火山 ASR 调用可借鉴，但目的不同（分析 vs 剪辑），脚本要另写
- "高光剪辑"——需看完整视频、识别高光、抽取拼接。目前无脚本，需另写
- 两者都是 main agent 的能力，所以脚本归 `crews/main/skills/video-product/scripts/`（或重构后的新 skill 目录），**不抽到公共 skills/**——content-producer 不用

### 4.5 state.py 阶段链重构

当前 state.py 的阶段链是 `script → gate0 → calibrate → assets → assemble → review → cover → deliver`，其中前三段（script/gate0/calibrate）都是 content-producer 范畴的事，重构后应砍掉。

**已定（用户 2026-07-25 拍板）**：`state.py` **main agent 用不上**——main agent 不出脚本、不走 Gate 0、不打分定稿，原有阶段链里前三段（script/gate0/calibrate）在 main 侧根本不存在，后五段（assets/assemble/review/cover/deliver）可由 SKILL.md 工作流文字直接表述，不需要脚本化状态机。

**落地约束**：
- `crews/main/skills/video-product/scripts/state.py` 在重构时**直接删除**（CP 侧的完整备份保留，CP 后续规划自己的状态机时可用）
- 不替代、不新写——main agent 视频生产工作流靠 SKILL.md 步骤文表述，不用脚本化 checkpoint
- 调研 todo 里不再为 state.py 列任何项

### 4.6 viral-chaser 与重构后 main agent 的衔接

参见 2.6 节。**已定**：viral-chaser 衔接按上一轮已改形态（viral-chaser 只管出脚本，制作委托 content-producer），main agent 不在中转。本节闭合，不另起开放问题。

### 4.7 封面制作的归属

**已定（用户 2026-07-25 拍板）**：封面制作**各自负责**——main agent 与 content-producer 都是直接调公共 `siliconflow-img-gen`，不额外抽公共封面 skill。具体封面制作要求（必须含标题文字、尺寸、设计感等）各自写在各自的对应技能文档里，不强行统一。

**落地约束**：
- 不抽 `video-cover-gen` 之类的公共 skill
- main agent 的封面要求继续写在 `crews/main/skills/video-product/SKILL.md` 的"制作封面"节
- content-producer 的封面要求由后续 CP 工作流规划时自行撰写（出发 1.3 范畴）
- 调研 todo 里不再为封面归属列任何项

---

## 5. 调研 todo 清单

> 调研期未完成的事项。全部完成后才进入"开发计划"撰写。

### 5.1 必须完成的调研项

- [x] **A. MoneyPrinterTurbo `app/` 目录结构调研**——已完成，见 3.4 节（clone 落 `~/wiseflow-pro/MoneyPrinterTurbo`，分层理清，含与出发点契合度复核 + 新暴露 Coverr/moviepy 两项）
- [x] **B. MoneyPrinterTurbo 素材匹配算法调研**——已完成，见 3.5 节（两套下载模式 + 时长匹配 + Coverr API 结论 + generate_terms prompt 模板借鉴判定）
- [x] **C. MoneyPrinterTurbo 字幕与 BGM 流程调研**——已完成，见 3.6 节（faster-whisper ASR 字幕 + moviepy BGM 混音均不引入 main 的判定 + 理由）
- [x] **D. MoneyPrinterTurbo 批量生成策略调研**——已完成，见 3.7 节（video_count 批量 + random shuffle 差异产生均不引入 main 的判定 + _run_pipeline 阶段链思路可参考）
- [x] **E. content-producer 已有视频技能的全景调研**——已完成，见 3.8 节（五技能职责矩阵 + 三条平行视频生产路径 + 与 main 重复风险复核：公共基础设施已共享无新重复）
- [x] **F. 公共 skills 命名约定调研**——已完成，见 3.9 节（平台-能力 / 能力 两格式约定成文 + 本轮新抽 aigc-video-gen/siliconflow-tts 复核通过）
- [x] **G. ui-demo 与 video-product 重构后的衔接调研**——已完成，见 3.10 节（WebM 产物与 assemble.py 兼容性确认——`.webm` 在 VIDEO_EXTS，normalize 阶段内置转码，无需外置转码步骤）
- [x] **H. 去口气词与高光剪辑的实现方式调研**——已完成，见 3.11 节（5 个开源项目调研 + viral-chaser 火山 ASR 复用确认 + 自写方案落 + cut_plan.py/apply_cut.py 骨架草案入 3.11.4）
- [x] **I. 当前 main agent video-product scripts 的依赖图调研**——已完成，见 3.12 节（6 个脚本全独立无互调 + 删除清单定：state.py 删、check.py 倾向保留待开发计划定 + 重构后目录预期）

### 5.2 调研完成后才做的事

- [x] J. 调研 todo 全完成后，把第 4 节开放问题统一发给用户拍板——**现状变更**：4.1/4.2/4.3/4.4/4.5/4.6/4.7 已在历轮回拍中闭合，第 4 节无残留开放问题，J 项可跳过
- [~] K. 用户拍板后，另起一份开发计划文档（不在本文件写），按调研结果与用户决策落地——**现状变更**：用户指示本轮先完成 main video-product skill 重构（已落地，见 2026-07-25 变更记录），独立开发计划文档待后续按需另起
- [~] L. 开发计划定稿后，更新本文件状态为"调研期结束 → 开发期开始"，本文件归档为开发计划的依据索引——**现状变更**：调研期已结束（todo A–I 全闭合 + 第 4 节无残留），main 重构已进开发期落地，本文件已作为依据索引使用中

---

## 6. 技能内容规范（强制）

> 本节是调研中暴露并固化的规范，**后续所有 skill 创建/修改都遵守**，不只针对 video-assembler。

### 6.1 规范正文

**SKILL.md 与 crew 专属 scripts（`crews/<crew>/skills/<skill>/scripts/` 下的脚本注释）是给 crew 看的工作指令**。crew 不知道产品上下游与开发判断——**禁写开发方案的词**：

- **开发判断**——"本轮据调研结论落地"、"决策 4.5 已定"、"范式配套"、"有意的边界"之类
- **产品功能取舍**——"不引入 faster-whisper 与 main stdlib 范式一致"、"用 ffmpeg 不引 moviepy"之类
- **参考来源**——"借鉴 OpenMontage Backlot"、"borrowed from MoneyPrinterTurbo"、"抄 Smart-Cut 的多层检测判据"之类

这些只能写 `docs/`（调研文档、开发计划文档），不能写进技能内。

### 6.2 判据

crew 是执行者，他只需知"调哪个脚本、传什么参数、产物落哪、verdict 含义"，不需知"为什么这么设计、参考了谁、与什么范式配套"。开发判断/取舍/参考来源对 crew 是噪音——既不帮他执行，又可能误导他质疑工作指令。

### 6.3 落地位置

| 内容类型 | 写哪 | 例 |
|---------|------|---|
| crew 工作指令（调脚本、参数、产物、verdict） | SKILL.md + scripts 注释 | "review.py verdict=pass 才交付" |
| 开发判断/产品取舍/参考来源/调研结论 | `docs/` | "MPT 字幕走 faster-whisper，不引入 main" |

### 6.4 自检清单（提交前扫）

技能改动提交前，在 SKILL.md + scripts 注释里 grep 以下关键词，命中即删净：

```
MoneyPrinterTurbo|MPT|参考仓|借鉴|调研|开发判断|产品取舍|有意的边界|范式配套|范式冲突|OpenMontage|gbro|Gate [0-9]|HyperFrames|Remotion|决策 [0-9]|本轮|据.*结论|据.*调研
```

例外：`docs/` 下的文档不限。

### 6.5 已清理记录

| 日期 | 文件 | 残留 | 处置 |
|------|------|------|------|
| 2026-07-25 | `video-assembler/SKILL.md` | "（与 assemble.py 范式配套，不烧字幕故无字幕检查）"、"（有意的边界）" | 删净 |
| 2026-07-25 | `video-assembler/scripts/assemble.py` L259 | "借鉴 OpenMontage Backlot 看板的 transition 能力，平替成 ffmpeg" | 删净 |
| 2026-07-25 | `video-assembler/scripts/review.py` L8/9/68/69/78 | "borrowed from OpenMontage post-render self-review + gbro Gate 3 QA"、"scoped to our ffmpeg-only no-Remotion/HyperFrames world"、"OpenMontage 抽 4 位，我们按其 + gbro Gate 3 的逐秒抽帧折中"、"OpenMontage 也用 5%" | 删净，同时 Usage 节 `./skills/video-product/` 路径订正为 `./skills/video-assembler/` |

---

## 7. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-07-25 | 文档初建，录入用户出发点 1.1–1.4，补齐现状盘点 2.1–2.7、MoneyPrinterTurbo 初步调研 3、开放问题 4、调研 todo 5 |
| 2026-07-25 | 用户回拍 4 条决策：viral-chaser 衔接已改（2.6 节闭合）、main agent 不接受脚本输入（4.1 节闭合）、去口气词/高光剪辑归 main agent（4.4 节闭合并从"调研范围"升为"开发范围"）、参考仓 clone 路径 `~/wiseflow-pro`（todo A/H 更新） |
| 2026-07-25 | 用户回拍 4.2/4.3/4.5/4.6 决策：4.2 命名自定（公共 `aigc-video-gen`，不绑平台；CP 侧 siliconflow-video-gen 保留不合并）；4.3 TTS 合并抽公共 `siliconflow-tts`，强制写明 OpenClaw 内置 TTS 优先、本脚本回退；4.5 state.py main 用不上直接删；4.6 viral-chaser 衔接已定不另起；4.7 封面各自负责不抽公共 |
| 2026-07-25 | 调研 todo A–I 全部闭合（3.4–3.12 节）：A MoneyPrinterTurbo app/ 分层 + Coverr/moviepy 暴露；B 素材匹配两套模式 + Coverr 不抽公共；C 字幕/BGM 不引入 main；D 批量不引入 main；E CP 五技能全景 + 三条平行路径 + 无新重复；F 公共命名约定成文；G ui-demo WebM 与 assemble.py 兼容无需转码；H 去口气词/高光剪辑自写方案 + cut_plan/apply_cut 骨架；I scripts 依赖图 + 删除清单（state.py 删、check.py 倾向保留）。第 4 节开放问题全闭合，J 项可跳过 |
| 2026-07-25 | **main video-product skill 重构落地**（进开发期）：①目录 git mv `crews/main/skills/video-product` → `crews/main/skills/video-assembler`，frontmatter `name: video-assembler` + 文内标题 + 脚本清单 6 处路径前缀全改；②删 `scripts/state.py`（决策 4.5 已定）；③SKILL.md 补两节：简单剪辑（extract_and_concat.py head/tail/slice/multi-segment）/ 成片自检强制闸门（review.py verdict pass/fail/warn）；④合成成品节加 `--transition crossfade` 可选段间溶接说明；⑤脚本清单表补 3 行（extract_and_concat/review）+ assemble 行加 crossfade 注。MPT 借鉴边界据调研结论 3.6/3.7 落地：字幕/BGM 走 ffmpeg 不引 moviepy、批量不引入、声画同出走公共 aigc-video-gen 不引 MPT services |
| 2026-07-25 | **回退一误判**：上轮把 `cut_plan.py` + `apply_cut.py` 误落进 video-assembler/scripts/，用户回拍明确**去口气词与高光剪辑是单独的两个技能，跟 video-assembler 完全没有关系**——删两脚本 + SKILL.md 删"去口气词/高光剪辑"节与脚本清单两行；调研文档 3.11.4/3.11.5 节结论修正：脚本草案改入独立技能（命名待开发计划定，候选 `filler-cut`+`highlight-cut` 或合一名 `smart-cut`），不胉 video-assembler，与 video-assembler 完全脱钩 |
