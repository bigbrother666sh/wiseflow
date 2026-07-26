# 小贝系统视频能力重新规划 — 调研与开发计划

> 起草日期：2026-07-25（周六）
> 状态：调研期（未进入开发）
> 用途：本文件用于**沉淀调研结果**与**规划出发点**，最终据此生成开发计划。开发计划不在本文件撰写，等调研结束另起一份。

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

- `youtube-publish`、`bilibili-publish` 两个技能暂时调整出代码仓，后面根据市场反馈再看。
- `ui-demo` 已调整至 main agent
- main agent 的 `video-produce` 技能调整到 content-producer，作为基础能力

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

#### 2.8 CP 侧五技能职责矩阵

| 技能 | 职责定位 | 视频生产路径 | 与 main 重构的重复风险 |
|------|---------|------------|---------------------|
| `collage-broll` | 把一句 ~5s 口播压成 editorial 纸拼贴组装动画（gbro 适配版） | Gate1 隐喻 → Gate2 siliconflow-img-gen 静帧 → Gate3 调公共 `aigc-video-gen` i2v 首尾帧插值出 5s 720x1280 无声/带声 MP4 | ❌ 无重复——属 CP 高级 B-roll，main 不做拼贴动画 |
| `html-video` | html-video 引擎模板驱动视频（23+ 模板，Content-Graph IR） | content-graph.json → 素材预获取（用户预置/video_generate/siliconflow-video-gen/pixabay/pexels）→ project-set-var 注入 → MiniMax TTS+BGM → hv.sh project-render | ⚠️ 素材预获取链与 main Stock Footage 重叠，但 html-video 是模板渲染范式，main 是 ffmpeg 直拼范式，**范式不同不重复** |
| `manim-explainer` | Manim 技术 explainer 动画（图/流程/架构/指标） | 定义视觉论点 → 拆 3–6 场 → 写 Manim 代码 → render-manim.sh 三档质量（low/medium/high）渲染 → 可 hand off 给 fragment-assembly + siliconflow-tts | ❌ 无重复——Manim 是科学动画，main 不做 |
| `design-system-picker` | 从内置 14 套设计系统库匹配风格规范（Stripe/Vercel/Linear/Notion/Apple/Supabase/Shopify/Figma/Spotify/Tesla/Framer/Airbnb/BMW/IBM/Starbucks） | `pick.sh "<风格描述>"` → 匹配 → 读 `./design-systems/<name>.md` 8 段规范（Visual Theme/Color/Typography/Components/Layout/Depth/Do's&Don'ts/Responsive） | ❌ 无重复——这是设计规范选择，不是视频生产，main 不做设计 |
| `init-workspace` | 为单项设计任务创建标准目录 + brief 模板 | `init.sh <任务名>` → `design_assets/YYYY-MM-DD-<任务名>/{brief.md,prompts.json,source/,output/}` | ⚠️ 与 main 的 `output_videos/<topic-en-slug>/` 工作区约定不同目录——**各自范式自洽，不强行统一** |

#### 2.9 CP 侧视频生产的三条平行路径

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

#### 2.10 与 main 重构的重复风险复核

| 维度 | main 重构后 | CP 现状 | 重复？ | 处置 |
|------|------------|---------|-------|------|
| 视频生成 AIGC | 公共 `aigc-video-gen` | 公共 `aigc-video-gen`（collage-broll Gate3）+ CP `siliconflow-video-gen` | ✅ 公共部分共享，不重复；CP 专属 siliconflow-video-gen 是另一家平台不合并 | 已落地 |
| TTS | 公共 `siliconflow-tts` | 公共 `siliconflow-tts` + MiniMax 扩展 | ✅ 公共部分共享，不重复；CP MiniMax 是另一条 TTS 路属 CP 范畴 | 已落地 |
| Stock Footage | 公共 `pexels-footage` / `pixabay-footage` | 同 | ✅ 完全共享，不重复 | 已落地 |
| 图像/封面 | 公共 `siliconflow-img-gen` | 同 | ✅ 完全共享，不重复 | 已是公共 |
| 工作区约定 | `output_videos/<topic-en-slug>/` | `design_assets/YYYY-MM-DD-<task>/`（init-workspace）+ `output_videos/<slug>/`（collage-broll 沿 xiaobei 路径契约） | ⚠️ CP 内部两套目录并存——设计任务走 design_assets，视频任务走 output_videos | **不强行统一**——main 用 output_videos，CP 视频也用 output_videos（collage-broll 已如此），CP 设计用 design_assets，各自自洽 |
| 简单剪辑 | main 专属 `extract_and_concat.py` + 去口气词 + 高光剪辑（待写） | CP 无 | ❌ 无重复——CP 不做基于已有素材的轻剪辑 | 已定 4.4 |
| 脚本生成 | main 不出脚本 | CP 范畴（待后续规划） | ❌ 无重复 | 已定 4.1 |

---

## 3. 调研

用户 2026-07-25 钦定 3 条调研原则：

1. **UI 层面完全不看**——只吸收能力，最终落地为 openclaw 的 Skill。被调研项目的 WebUI、API controller、前端组件、CLI 交互等 UI 范式全部跳过，不调研、不借鉴。
2. **大模型/AIGC 模型的 Provider 适配层完全不看**——模型的调用适配统一按上一轮抽出的公共模块（如 `skills/aigc-video-gen/`、`skills/siliconflow-img-gen/`、`skills/siliconflow-tts/`、未来 CP 侧的 llm skill 等）。被调研项目里 `services/llm.py`、`services/voice.py` 的七条 TTS 路径、`services/material.py` 里的 Pexels/Pixabay/Coverr API key 轮转、各种 SDK 适配——**只看算法不抄适配层**。
> - 落地成 Skill 时，调的是本仓已有公共模块，不重新引入被调研项目的 SDK 适配层
3. **重点是看"怎么出脚本"**——尤其是像 MoneyPrinterTurbo 这种素材匹配算法（脚本 → 关键词 → 时长 → 素材挑选）。其余如视频合成技术细节、字幕烧录方式等次之。

### 3.1 MoneyPrinterTurbo

- 一站式 AI 短视频生成工具
- 用户只提供视频**主题**或**关键词**，自动生成：视频脚本 → 匹配素材 → 生成字幕和背景音乐 → 合成高清短视频
- 四种使用方式：AI Agent / WebUI / API / CLI
- 代码按控制器、服务、模型等职责分层（`app/` 目录）
- 调研代码仓一律放：`~/wiseflow-pro/` 下

#### 能力特性（从 README 摘录）

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

#### 借鉴判定

**⚠️ 不建议引入到 main**——理由四：

1. **main 不出脚本**——MPT 的批量差异靠"同脚本不同素材顺序"，main 没脚本就没了批量的意义前提。main 的"组装"是用户给定素材清单，顺序由 agent 定，shuffle 反而破坏用户意图
2. **main 走逐段确认**——`compress_preview.py` + SKILL.md 明示"逐段发用户确认"，单产物已是慢流程；批量 N 产物会把每段确认膨胀 N 倍，用户体验崩
3. **声画同出模型无批量差异**——main 的 gen.py 走百炼/火山声画同出，同 prompt 同 seed 出同产物，批量要靠 prompt/shuffle 变；MPT 的素材 shuffle 范式不适用 gen.py 声画同出
4. **"挑最满意"在 main 范式下退化为 review.py**——main 已有 `review.py` 成片自检闸门（ffprobe + 抽帧黑屏扫描 + 音频电平 + 时长分辨率一致性），verdict pass/fail/warn，**这已是"挑"的逻辑**——不及格的修或重，及格的交付。引入"多产物挑最满意"无增量价值

**借鉴结论**：
- ❌ `video_count` 批量机制不引入 main——与逐段确认 + 声画同出 + review.py 范式冲突
- ❌ random shuffle 差异产生不引入——破坏用户素材顺序意图
- ✅ **`_run_pipeline` 的固定阶段链思路可参考**——main 重构时若重写 state.py（已定 4.5 删），可仿此"script→terms→audio→...→final"的阶段定义写 SKILL.md 工作流文（仅参考思路，不抄代码，也不上脚本化状态机——4.5 已定 main 用不上 state.py）

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

## 5. 技能开发规范（强制）

### 5.1 规范正文

**SKILL.md 与 crew 专属 scripts（`crews/<crew>/skills/<skill>/scripts/` 下的脚本注释）是给 crew 看的工作指令**。crew 不知道产品上下游与开发判断——**禁写开发方案的词**：

- **开发判断**——"本轮据调研结论落地"、"决策 4.5 已定"、"范式配套"、"有意的边界"之类
- **产品功能取舍**——"不引入 faster-whisper 与 main stdlib 范式一致"、"用 ffmpeg 不引 moviepy"之类
- **参考来源**——"借鉴 OpenMontage Backlot"、"borrowed from MoneyPrinterTurbo"、"抄 Smart-Cut 的多层检测判据"之类

这些只能写 `docs/`（调研文档、开发计划文档），不能写进技能内。

### 5.2 判据

crew 是执行者，他只需知"调哪个脚本、传什么参数、产物落哪、verdict 含义"，不需知"为什么这么设计、参考了谁、与什么范式配套"。开发判断/取舍/参考来源对 crew 是噪音——既不帮他执行，又可能误导他质疑工作指令。

### 5.3 落地位置

| 内容类型 | 写哪 | 例 |
|---------|------|---|
| crew 工作指令（调脚本、参数、产物、verdict） | SKILL.md + scripts 注释 | "review.py verdict=pass 才交付" |
| 开发判断/产品取舍/参考来源/调研结论 | `docs/` | "MPT 字幕走 faster-whisper，不引入 main" |
