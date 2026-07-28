# content-producer 重构开发计划

> 起草日期：2026-07-27（周一）
> 依据：`docs/video-capability-replanning-2026-07-25.md` §1–§9（用户已批示）
> 状态：开发计划（待用户拍板后进入执行）
> 范围：仅 content-producer 侧 + 受波及的公共 skill。main agent 侧不在本文件修改范围。
> 本文件是开发方案与产品取舍归属地——技能内（SKILL.md / crew scripts 注释）禁出现本文件用词，按调研文档 §5 强制规范。

---

## 0. 落地后 CP 的能力全景（一张图）

重构后 content-producer 共四条能力方向，每条对应一个独立技能：

| # | 能力方向 | 技能名（拟定） | 性质 | 一句话定位 |
|---|---------|---------------|------|-----------|
| 1 | **端到端全流程视频制作** | **`video-producer`** | 新建（主技能） | 出脚本 → 分镜 → 机位一致性 → 素材匹配 → 闸门 → 渲染 → 自检 → 交付。CP 视频生产主入口，按 HyperFrames 三层架构组织 |
| 2 | **纸拼贴组装动画** | `collage-broll` | 已有，保留 | 一句口稿压成 editorial 纸拼贴 5s B-roll，三闸门审批，Gate3 调公共 `aigc-video-gen` i2v |
| 3 | **技术演示视频** | `manim-explainer` | 已有，保留 | Manim 科学动画（图/流程/架构/指标），三档渲染，可 hand-off |
| 4 | **平面设计全案** | **`design-full`** | 新建（合并自 `design-system-picker` + `init-workspace` + AGENTS.md 工作模式 2） | 完整网页/落地页/APP 界面/品牌视觉体系。含 brief 确认、设计系统选取、视觉 review 全工作流 |

**删除**：`crews/content-producer/skills/video-product/`（仅占位符 + main 副本，§9.2 已变更以现状为准，本计划不保留此占位）

**禁入 CP**（BUILTIN_SKILLS 清单同步删）：`html-video` / `siliconflow-video-gen` / `siliconflow-tts` / `ui-demo` / `bilibili-publish`

> 调研文档 §8.4 #34 已定方法论：吸收外部 skill 时"原子能力可整体吸收，workflow 路由不可吸收"。CP 的四条能力方向就是四个 workflow 路由入口，彼此不互相调用——`collage-broll` / `manim-explainer` / `design-full` 是已定型的三条窄路径，`video-producer` 是新主路径。四条路径共享公共 domain skill（见 §1.2）。

---

## 1. 技能架构（三层）

按调研文档 §8.4 #31 + §9.3 决策 1（用户钦定"同意"三层架构）：

### 1.1 三层定义

```
Layer A  crew AGENTS.md                    "我是谁、能做哪四件事、收到活儿先看哪"——CP 入口路由
Layer B  四个 creation workflow skill      "走哪条路、那条路的闸门与产物"——工作流路由
Layer C  公共 domain skill（skills/）      "原子能力，永不着端到端交付物"——执行底座
```

**Layer A** = `crews/content-producer/AGENTS.md`：把现"工作模式 1/2"重写成"四条能力方向"路由表，首个匹配行即执行。每行指向 Layer B 的一个 workflow skill。不再写细节工作流——那些下沉到对应 skill 里。

**Layer B** = 四个 creation workflow skill：
- `crews/content-producer/skills/video-producer/`（新建，端到端主链）
- `crews/content-producer/skills/collage-broll/`（已有）
- `crews/content-producer/skills/manim-explainer/`（已有）
- `crews/content-producer/skills/design-full/`（新建，整合 design-system-picker + init-workspace + AGENTS.md 工作模式 2）

**Layer C** = 公共 domain skill（`skills/` 下），CP 与 main 共用：
- `skills/aigc-video-gen`（已抽，§9.1 已闭环）
- `skills/siliconflow-img-gen`（已是公共，封面 / collage-broll Gate2 / 设计素材）
- `skills/awk-tts`（**新建**，由现 `skills/siliconflow-tts` 改造为火山 seed-tts-2.0，§2）
- `skills/pexels-footage` / `skills/pixabay-footage`（已是公共，素材补充）
- `skills/video-review`（成片自检闸门，§3 处置后定 CP 是否引用）

### 1.2 domain skill 硬规则（§8.4 #33）

Layer C 永不接管端到端交付物。具体落地：
- `aigc-video-gen` 只出片段，不出成片；成片组装走 `video-producer` 内脚本
- `awk-tts` 只出音频，不出视频；视频用音频混音走 `video-producer` 内脚本
- `siliconflow-img-gen` 只出图，不做封面合成；封面合成走对应 workflow skill
- `video-review` 只审成片，不决定交付；交付与否由 workflow skill 按 verdict 处置

---

## 2. 公共 skill 改造：`siliconflow-tts` → `awk-tts`

### 2.1 改造目标与边界

调研文档用户批示："`siliconflow-tts` 也得从 siliconflow 切换到 awk（火山），类似我们对 siliconflow-img-gen 的改造。awk 这边的 api 文档见火山引擎语音合成 2.0。使用 seed-tts-2.0（字符版）。开通方式也跟 siliconflow-img-gen 以及 viral-chase 中火山 asr 类似（开通管理 → 语音模型 → 最下 "Doubao-语音合成-2.0" 立即使用 → 试用，然后在这个页面拿到 Access Token / APP ID / Secret Key，这个一开始送 2 万字符）。"

**改造边界**（与 `siliconflow-img-gen` 改造同范式）：
- 仓内文件级改造：本仓 `skills/siliconflow-tts/` 整目录重命名为 `skills/awk-tts/`，`SKILL.md` frontmatter `name` 改 `awk-tts`，`homepage` 改火山文档 URL，`primaryEnv` 改 `VOLC_TTS_*`，`description` 改为火山 seed-tts-2.0
- 脚本改造：`scripts/tts.py` 重写为调火山方舟 ARK HTTP API（与 `siliconflow-img-gen` 同走 `ARK_API_BASE` + `ARK_API_KEY`/`AWK_API_KEY` 双头兼容），模型 ID 用 `seed-tts-2.0`（字符计费版）
- 优先级约定保留：OpenClaw 内置 TTS 优先 → 本脚本 fallback（这条不因平台切换而变）
- 依赖：火山 seed-tts-2.0 走 HTTP，仅需 `requests`（已在仓根 `requirements.txt`），不引入 SDK
- `ASR Self-Check` 环节：原 siliconflow-tts 用 SiliconFlow ASR 自检；改造后用火山 ASR（`VOLC_ASR_*`，与 viral-chaser 同凭据池）做自检，仍走 Jaccard 0.5 阈值

### 2.2 环境变量与凭据

沿用火山 ARK 统一头：

| 变量 | 说明 |
|------|------|
| `AWK_API_KEY`（或 `ARK_API_KEY`） | 火山方舟 ARK API key（与 `siliconflow-img-gen` / `collage-broll` Gate2 同凭据池） |
| `ARK_API_BASE` | 可选，默认 `https://ark.cn-beijing.volces.com/api/v3` |
| `VOLC_ASR_APP_ID` + `VOLC_ASR_ACCESS_KEY` | 自检用火山 ASR 凭据（与 `viral-chaser` 同凭据池，复用） |

> 开通引导：与 viral-chaser ASR 同范式——用户在火山控制台「开通管理 → 语音模型 → Doubao-语音合成-2.0 → 立即使用 → 试用」拿 Access Token / APP ID / Secret Key。但因 seed-tts-2.0 走 ARK 统一头，实际只需要 `AWK_API_KEY`（与图像同控制台拿一次即可，不另开），自检才需要 ASR 那对凭据。开通引导措辞写 SKILL.md 首次使用节，**不写开发判断**。

### 2.3 落地清单

1. `git mv skills/siliconflow-tts skills/awk-tts`
2. `git mv skills/awk-tts/siliconflow-tts.sh skills/awk-tts/awk-tts.sh`（wrapper 改名）
3. 重写 `skills/awk-tts/SKILL.md`：frontmatter `name: awk-tts`、`primaryEnv: AWK_API_KEY`、`homepage: https://docs.volcengine.com/docs/6561/1829010`、`description` 改为火山 seed-tts-2.0；正文保留"内置 TTS 优先"优先级约定、参数表、ASR 自检节，但所有 SiliconFlow 字样与变量名替换为火山
4. 重写 `skills/awk-tts/scripts/tts.py`：调火山 ARK `audio/speech` 端点，model id `seed-tts-2.0`（字符计费版）；保留 `--text` / `--text-file` / `--voice` / `--format` / `--output` / `--out-dir` / `--speed` / `--overwrite` / `--no-asr-check` 参数语义；voice id 改为火山侧音色列表（首版列 5–8 个，标注情绪/性别/语速，与原 siliconflow 的 benjamin/charles/claire/david/diana 一一对应或最接近者）
5. 改写 `skills/awk-tts/awk-tts.sh` wrapper 内 `exec python3 .../scripts/tts.py` 路径自洽
6. 仓根 `requirements.txt`：现已有 `requests`，无需改
7. 各引用方更新：
   - `crews/content-producer/skills/collage-broll/SKILL.md`：当前未直接调 TTS（Gate3 走 gen.py 声画同出），不涉及
   - `crews/content-producer/skills/manim-explainer/SKILL.md`：现引用 `siliconflow-tts`，改 `awk-tts`
   - `crews/main/skills/video-edit/SKILL.md`：现引用 `siliconflow-tts`（audio-mix 旁白回退），改 `awk-tts`
   - `crews/main/skills/talking-head-cut/SKILL.md`：不调 TTS，不涉及
   - 全仓 `grep` 一遍 `siliconflow-tts` 字面量引用，确保无断链
8. 旧 `crews/content-producer/skills/siliconflow-tts/` 副本：调研文档 §4.3 已定应删本地副本改引公共，本计划执行时一并 `git rm -r crews/content-producer/skills/siliconflow-tts/`

### 2.4 不做的

- 不保留 SiliconFlow 双平台兼容——彻底切换，旧 `fnlp/MOSS-TTSD-v0.5` voice id 不留 fallback
- 不引入 MiniMax 扩展（调研文档 §2.9 提到的 html-video 走 MiniMax，但 html-video 整体已从 CP 移除，不涉及）

---

## 3. 公共 skill 处置：`video-review`

### 3.1 评估结论：保留为公共

`video-review` 是成片自检闸门（ffprobe + 5 位抽帧黑帧扫 + 音频电平 + 时长/分辨率一致性，verdict pass/fail/warn），由 main 侧 2026-07-26 抽入公共并补了薄 wrapper。

- **main 侧**：`video-edit` / `talking-head-cut` 均明示"成片交付前必跑 video-review，verdict=pass 才交付"——**main 强依赖**，不能删
- **CP 侧**：`video-producer` 主链的成片交付闸门同样走 `video-review`（§4 详述）；`collage-broll` Gate3 出片后做 contact sheet QA，可补一道 `video-review` 做技术自检；`manim-explainer` 渲染产物也可走

**结论**：`video-review` 保留为公共 skill，不作处置。CP 侧新写工作流里在成片交付节统一引用即可，不另建 CP 专属副本。

### 3.2 不下沉为各技能内脚本的理由

- 三条视频出片路径（video-producer / collage-broll / manim-explainer）+ main 两条（video-edit / talking-head-cut）共用同一份 ffprobe/抽帧/电平判据，下沉会造成 5 处重复实现
- verdict JSON schema 是跨技能契约（pass/fail/warn + critical[] + warnings[]），下沉后各技能各自演化会撕裂
- 调研文档 §8.5 #48 已点明：`video-review` 是技术层自检，与 §8.5 #48 slideshow_risk（pre-compose 的"计划"评估）**不重叠而是互补**——后者是 CP 主链独有的新闸门，下沉到 `video-producer` skill 内（§4.5）

---

## 4. CP `AGENTS.md` 重构

### 4.1 重构目标

调研文档用户批示："`Agents.md` 也需要按照上述的思路重新整理。但这里目前的 '## 工作模式 2：平面设计全案' 里面包含了很细节的工作流程描述，这个也许应该单独地列一个 skill，而不是放在 `Agents.md` 里边。可以考虑同时整合 design-system-picker 和 init-workspace。"

落地：
- 现 AGENTS.md "工作模式 1：端到端视频生产"（仅一行 + 占位）→ 扩成四条能力方向路由表
- 现 AGENTS.md "工作模式 2：平面设计全案"（含工作流 A/B/C + 设计 token 规范 + 品牌原则，~180 行）→ **整体抽到新 skill `design-full`**，AGENTS.md 不留细节
- AGENTS.md 通用规则节里"任务文件夹 / Brief 确认 / 设计系统选取 / 视觉 Review"四小节是 design-full 工作流的组成部分，同步抽走

### 4.2 新 AGENTS.md 骨架

```markdown
# content-producer — Workflow

我是专业内容制作者，接到活儿先按下表选一条路，**首个匹配行即执行**，不向下评估。

## 能力方向路由

| 入口信号 | 走哪条路 | 入口技能 |
|---------|---------|---------|
| 用户要"从零做视频""出一支完整视频""按这个脚本/主题拍片子" | 端到端视频制作 | `video-producer` |
| 用户要"把这句话/这句口播做成拼贴 B-roll""纸拼贴动画""半调拼贴" | 纸拼贴组装动画 | `collage-broll` |
| 用户要"用 Manim 做技术演示""流程图/架构图动起来""指标可视化动画" | 技术演示视频 | `manim-explainer` |
| 用户要"做网页/落地页/APP 界面/品牌视觉体系"等平面设计 | 平面设计全案 | `design-full` |

## 通用约定

- **每接到一个活儿先建工作区**：视频类走 `output_videos/<topic-en-slug>/`，平面设计类走 `design_assets/YYYY-MM-DD-<任务名>/`（由 `design-full` 内脚本建）
- **Brief 确认前不得干活**：任何方向都先把需求整理成 brief，发用户确认后再进后续
- **成片/成稿交付前必跑自检**：视频走公共 `video-review`，平面设计走视觉 review（对照 brief + DESIGN.md）
- **封面**：交付成片视频必须配含标题文字的封面图，走公共 `siliconflow-img-gen`
- **不许声称没做过的事**：没有 tool result 或产物文件证明，不许声称已生成/已渲染/已改动（调研文档 §8.4 #41）
- **平台运营不在 CP**：发布到抖音/B站/小红书等归 main agent 的各 publish 技能，CP 不碰

## 衔接关系

- **viral-chaser → CP**：main agent 的 viral-chaser 只出追爆报告，制作委托 CP。接手时把报告当 brief 的一部分，走 `video-producer` 的 reference-driven 阶段——**CP 只吃报告出 2–3 个差异化概念 + 成本**，不做视频下载/转写/抽帧（那是 viral-chaser 的活，CP 不重复造）；无报告则跳过该阶段直入出脚本
- **main 的 video-edit → CP**：用户要从零做视频 → 转 CP 的 `video-producer`；用户给已有素材要轻剪辑/拼接/烧字幕 → 仍归 main 的 `video-edit`
- **main 的 talking-head-cut**：口播类去口气词/高光剪辑归 main，CP 不做
```

### 4.3 不写进 AGENTS.md 的

- 任何方向的具体工作流步骤 → 下沉到对应 skill SKILL.md
- 设计 token / 品牌原则 / 工作流 A/B/C → 下沉到 `design-full`
- video-producer 的阶段链 / 闸门定义 / 素材匹配算法 → 下沉到 `video-producer`
- 调研结论 / 开发判断 / 参考来源（MoneyPrinterTurbo / OpenMontage / ViMax / HyperFrames / html-video）→ 不进 AGENTS.md，只在 `docs/`

---

## 5. 新建 `crews/content-producer/skills/design-full/`（平面设计全案）

### 5.1 整合范围

- 现 `design-system-picker` skill 整目录 → 并入 `design-full`（设计系统选取成为 design-full 的一个子环节）
- 现 `init-workspace` skill 整目录 → 并入 `design-full`（建任务文件夹成为 design-full 的 Step 1）
- 现 AGENTS.md "工作模式 2" 全部内容（工作流 A/B/C + 设计 token + 品牌原则）→ 并入 `design-full` SKILL.md
- 现 AGENTS.md 通用规则里"任务文件夹 / Brief 确认 / 设计系统选取 / 视觉 Review"四小节 → 并入 `design-full`

### 5.2 design-full SKILL.md 骨架

```markdown
---
name: design-full
description: 平面设计全案——完整网页/落地页、APP/产品界面、品牌视觉体系。从需求 brief 到设计系统选取、素材获取、HTML/CSS 编写、视觉 review、交付归档的完整工作流。接到"做网页/落地页/APP 界面/品牌视觉"类需求时走本技能。
metadata:
  openclaw:
    emoji: 🎨
    requires:
      bins:
        - python3
---

# 平面设计全案（design-full）

## 适用场景

用户要做以下任一平面设计工作：
- 完整网页 / 落地页 / 团队介绍 / 404 页等
- APP / 产品界面 / 管理后台 / SaaS 面板原型
- 品牌视觉体系（色彩/字体/组件/间距规范）

不适用：视频制作（→ `video-producer` / `collage-broll` / `manim-explainer`）

## Step 1：建工作区

[调 init-workspace 的 init.sh，落 design_assets/YYYY-MM-DD-<任务名>/]

## Step 2：Brief 确认（强制闸门）

[把需求整理成 brief.md，发用户确认，确认前不进后续]

## Step 3：设计系统选取

[调 design-system-picker 的 pick.sh，匹配 1–3 套，发用户确认选定，写入 DESIGN.md]

## Step 4：素材获取

[页面配图/背景 → pexels-footage / pixabay-footage 优先，siliconflow-img-gen 备选，落 source/]

## Step 5：HTML + CSS 编写

[CSS custom properties 定 token，严格遵循 DESIGN.md；语义化标签；响应式；状态完备]

## Step 6：视觉 Review（强制闸门）

[用 image 工具看生成结果，对照 brief.md + DESIGN.md 逐项查，最多 3 轮调整]

## Step 7：交付归档

[output/ 落成品，更新 index.md]

---

## 三条子工作流（按任务类型择）

### 工作流 A：完整网页 / 落地页设计
[从现 AGENTS.md 工作流 A 整段迁入]

### 工作流 B：APP / 产品界面设计
[从现 AGENTS.md 工作流 B 整段迁入]

### 工作流 C：品牌视觉体系构建
[从现 AGENTS.md 工作流 C 整段迁入]

---

## CSS 设计 Token 规范
[从现 AGENTS.md 整段迁入]

## 品牌规范应用原则
[从现 AGENTS.md 整段迁入]
```

### 5.3 子脚本归属

| 现 skill | 现 script | design-full 内归属 |
|---------|-----------|-------------------|
| `init-workspace/scripts/init.sh` | 建任务文件夹 + brief 模板 | `design-full/scripts/init.sh`（Step 1 调） |
| `design-system-picker/scripts/pick.sh` | 按风格描述匹配设计系统 | `design-full/scripts/pick.sh`（Step 3 调） |
| `design-system-picker/design-systems/*.md` + `index.json` | 14 套设计系统规范库 | `design-full/design-systems/`（随 skill 整合迁入） |

### 5.4 落地清单

1. `mkdir -p crews/content-producer/skills/design-full`
2. 把现 `design-system-picker/design-systems/` 整目录 `git mv` 到 `design-full/design-systems/`
3. 把现 `design-system-picker/scripts/pick.sh` + `design-system-picker/design-system-picker.sh` `git mv` 到 `design-full/scripts/` 与 `design-full/`（wrapper 改名 `design-full.sh`，内部 exec 路径自洽）
4. 把现 `init-workspace/scripts/init.sh` + `init-workspace/init-workspace.sh` `git mv` 到 `design-full/scripts/` 与 `design-full/`（wrapper 改名并入）
5. 写 `design-full/SKILL.md`（按 §5.2 骨架，从现 AGENTS.md 工作模式 2 整段迁移工作流 A/B/C + 设计 token + 品牌原则）
6. `git rm -r crews/content-producer/skills/design-system-picker crews/content-producer/skills/init-workspace`（旧 skill 整目录删）
7. 全仓 `grep` 一遍 `design-system-picker` / `init-workspace` 字面量引用，更新到 `design-full`
8. CP `BUILTIN_SKILLS` 与 `DENIED_SKILLS` 不显式列 design-full（它本就是 CP 专属，走 CP skills 自动发现）

### 5.5 不做的

- 不为 design-full 抽公共 design-system-picker——平面设计是 CP 专属能力，main 不做（调研文档 §2.10 已定），不上移到 `skills/`
- 不引入 HyperFrames `frame.md` 那层"为镜头反转"（调研文档用户批示："不必 design-system-picker 完全是 CP 的另一个能力"，§9.3 决策 7）

---

## 6. 新建 `crews/content-producer/skills/video-producer/`（端到端主技能）

### 6.1 定位与边界

**这是 CP 重构的核心产出**。调研文档 §1.1 已定：CP 独占"出脚本 + 其余视频能力"——main agent 不出脚本、不做端到端制作，全归本技能。

- **入口**：用户给主题/关键词/已有脚本/已有素材中的任一组合，要求"做一支完整视频"。另可接收**main agent 喂入的 viral-chaser 追爆报告**（作为 brief 的一部分，CP 不自己做视频下载与分析——那是 viral-chaser 的活，调研文档 §2.6 已定 viral-chaser 只管出报告、制作委托 CP）
- **出口**：含封面图的成片 MP4 + 自检 verdict=pass + 用户确认
- **不做**：
  - 拼贴 B-roll（→ collage-broll）、Manim 科学动画（→ manim-explainer）、平面设计（→ design-full）、已有素材轻剪辑（→ main 的 video-edit）
  - **视频下载与爆款分析**——本仓 `viral-chaser` 已完善（下载 + 火山 ASR 转写 + 关键帧 + 报告），CP 不重复造；接到"参考某爆款/某链接做片子"时，若 main 喂入了 viral-chaser 报告就吃报告出脚本，若没喂就先请 main 跑 viral-chaser，CP 不自带任何下载/转写/抽帧环节

### 6.2 阶段链（11 段，每段显式写出 7 项 metadata）

按调研文档 §8.4 #35 + #36，每段写明：`produces` / `required_artifacts_in` / `tools_available` / `checkpoint_required` / `human_approval_default` / `review_focus` / `success_criteria`。统一骨架（When to Use / Prerequisites 表 / Process / Self-Evaluate / Submit / Common Pitfalls / Gate Reminder，§8.4 #36）。

```
Stage 0  intent-router        意图路由 → 三档脚本模板（narrative/motion/montage）
Stage 1  reference-driven     若 main 喂了 viral-chaser 报告 → 吃报告出 2–3 差异化概念 + 成本；无报告则跳过本阶段直入 Stage 2。CP 不自带视频下载/转写/抽帧
Stage 2  develop-story        idea → 故事（含受众/类型显式复述，100–200 词梗概，人物，分场）
Stage 3  write-script         故事 → 分场剧本（同时间同地点分一场；可拍化描述；enhancer 润色）
Stage 4  storyboard           剧本 → 镜头表（每镜叙事目的 / 机位复用 / 位置朝向 / 不写不可见）
Stage 5  shot-decompose       每镜拆首帧静照 / 尾帧静照 / 运动描述（variation_type 三档）
Stage 6  character-registry   角色三视图 front/side/back + static/dynamic features 拆分
   ────── GATE A：文本闸门（脚本+分镜+机位+角色全齐，停，发用户审）──────
Stage 7  slot-plan            素材 slot 规划（template + hero slot + tone→slot 数）
Stage 8  asset-resolve        按 slot 拉素材（Fast path：多源并发搜 + 缩略图人核 + rejected_picks 落盘）
Stage 9  pre-compose-gates    slideshow_risk 六维 + delivery_promise 锁定 + motion_ratio 预估
   ────── GATE B：素材闸门（素材齐 + 计划过审，停，发用户看 contact sheet）──────
Stage 10 render               按 slot 渲染（AIGC 走 aigc-video-gen i2v 首尾帧插值；静图走 siliconflow-img-gen）
Stage 11 audio-mix            旁白（awk-tts）+ BGM 混音 + 字幕烧录
Stage 12 assemble             按镜头顺序拼接成片 + 转场（如计划有）
Stage 13 self-review          公共 video-review 技术自检 + CP 侧 motion_led 抽查
Stage 14 cover + deliver      封面（siliconflow-img-gen，必含标题文字）+ 用户确认
```

> Stage 0–6 全是**文本产物**，调研文档 §8.4 #40 已定"付费生成前必停"——GATE A 落在这条边界上，是闸门的最自然定义。GATE B 落在素材就绪、pre-compose 闸门通过后，确认渲染前最终计划。

### 6.3 各阶段吸收清单（调研文档 §8 判定映射到阶段）

| 阶段 | 吸收条目（§8 编号） | 判定 | 落地形态 |
|------|------------------|------|---------|
| Stage 0 intent-router | §8.1 #1, #2, #3 | A | 三档模板 + 三硬约束（禁隐喻/禁机位术语/对白引号格式）+ develop_story 两段式写进 stage 文 |
| Stage 1 reference-driven | §8.4 #46, #47 | A/B | **不做视频下载/分析**——只接 main 喂入的 viral-chaser 报告当输入，出 2–3 差异化概念 + 成本；无报告则跳过本阶段。"贴参考片→分析→10–15s 试片"这条原 OM 范式中的下载与转写环节归 viral-chaser，CP 不自带 |
| Stage 2 develop-story | §8.1 #3, #4 | A | 场次划分原则（同时间同地点）；script_enhancer 为精度允许冗余 + 每次对白重复音色描述 |
| Stage 3 write-script | §8.1 #5, #6, #7, #8, #9 | B | 叙事弧时间预算（HOOK/SETUP/BUILD/CLIMAX/LANDING）+ 中文字数预算表（需实测 awk-tts 中文语速）+ enhancement_cues 六型 + delivery_cues + 自评 N 维 |
| Stage 4 storyboard | §8.2 #18 | A | storyboard 硬规则六条（每镜叙事目的/机位复用/位置朝向/不写不可见/每镜每角色最多一句/自包含） |
| Stage 5 shot-decompose | §8.2 #11, #12, #13 | A | 首尾帧三拆 + 运动描述禁角色名用外观特征 + variation_type 三档定传 1 张/2 张参考图 |
| Stage 5b camera-tree | §8.2 #14 | B | 转场视频取帧法。**用户批示问"ffmpeg 是不是自带转场功能"**——ffmpeg 的 xfade/crossfade 是**合成期转场**（Stage 12），不是机位连续性。camera_tree 解的是"A 新机位首帧不从零生成"，需先实跑一次成本实测再定是否引入；首版**判 C 不引入**，机位连续性退化成"新机位首帧从父机位首帧编辑生成 + siliconflow-img-gen 重绘"，Stage 12 用 ffmpeg xfade 做合成期转场 |
| Stage 6 character-registry | §8.2 #15, #16, #17 | A | 三视图 + static/dynamic 拆分 + best_image_selector 三轴择优（退化成"agent 看 contact sheet 人核"，不引入 CLIP，§9.3 决策 3） |
| Stage 7 slot-plan | §8.3 #19, #20, #21, #22 | A/B | tone→slot 数表（中文短视频需重标定）+ slot description 模板 + description/query 分职 + hero slot |
| Stage 8 asset-resolve | §8.3 #23, #26, #27, #28, #30 | A | 按判断挑不按分数挑 + rejected_picks 落盘 + 儿童 source lock + media-use resolve 一动词 + media opportunity pass 四纪律 + 用户素材必先 probe |
| Stage 8 asset-resolve | §8.3 #24 | C（Fast path A） | 不引入 CLIP/torch，走 Fast path 多源并发搜 + 缩略图人核（§9.3 决策 3） |
| Stage 8 asset-resolve | §8.3 #25 | C | 不扩充图库源，保 Pexels + Pixabay（§9.3 决策 4） |
| Stage 9 pre-compose-gates | §8.5 #48, #49 | A（★） | slideshow_risk 六维打分（≥4.0 fail 不许进 compose）+ delivery_promise 八类锁定 + motion_ratio 阈值（"给静图加转场不算动态"） |
| Stage 10 render | §8.5 #50 | A | lint → check → preview → render 顺序纪律（本阶段若用 HF-style 渲染适用；AIGC 路径退化为"先单镜试渲染再批量"） |
| Stage 11 audio-mix | §8.1 #8 | B | delivery_cues 按 awk-tts 实际通道能力裁剪；OpenClaw 内置 TTS 优先 → awk-tts fallback |
| Stage 13 self-review | §8.5 #48, #51 | A | 公共 video-review 技术层 + CP 侧 motion_led 抽查（"成片里真实运动镜头占比是否兑付 delivery_promise 承诺"） |
| 全阶段通用 | §8.4 #37, #38, #41, #42 | A | Gate Reminder 措辞 + 返工/耗时上限 + "不许声称没做过的事" + 模糊意图不算确认 |
| 全阶段通用 | §8.4 #39 | A（★） | artifact-file-as-checkpoint：每步先查产物文件存在则 load，不存在才生成——**不引状态机脚本**（调研文档 §4.5 已判 CP 需断点续跑但不上 state.py） |
| 全阶段通用 | §8.4 #44, #45 | A（★） | 决策审计链 + 预算四步全量原汁原味吸收（§9.3 决策 6 用户批示"先全量，使用中再改进"） |

### 6.4 工作区目录约定

```
output_videos/<topic-en-slug>/
├── brief.md                    # Stage 0/1 产出：意图路由 + 概念选项 + 用户选定
├── reference-driven/           # Stage 1（可选，仅当 main 喂了 viral-chaser 报告）
│   ├── viral-chaser-report.md  # main 喂入的追爆报告原档（CP 不自己跑 viral-chaser）
│   ├── concepts.md             # 据报告出的 2–3 差异化概念 + 成本 + 备选路径
│   └: 无下载产物、无 transcript、无关键帧——那些归 viral-chaser，CP 不自带
├── script/
│   ├── story.md                # Stage 2
│   ├── script.md               # Stage 3（含 enhancement_cues 六型 + delivery_cues）
│   ├── budget.json             # 预算四步：estimate
│   ├── decisions.json          # 决策审计链（跨阶段累积）
├── storyboard/
│   ├── storyboard.json         # Stage 4 镜头表
│   ├── shot_decompose.json     # Stage 5 首尾帧+运动描述+variation_type
│   ├── camera_tree.json        # Stage 5b（若引入）
├── characters/
│   ├── registry.json           # Stage 6 static/dynamic features
│   ├── <char-id>/front.png     # 三视图
│   ├── <char-id>/side.png
│   └── <char-id>/back.png
├── gates/
│   ├── gate-a.md               # GATE A 文本闸门评审产物
│   ├── gate-b.md               # GATE B 素材闸门评审产物
├── slots/
│   ├── slot-plan.json          # Stage 7
│   ├── asset-resolve.json      # Stage 8（含 rejected_picks）
│   ├── slideshow-risk.json     # Stage 9 六维打分
│   ├── delivery-promise.json   # Stage 9 承诺锁定
├── render/
│   ├── shot-NN/                # Stage 10 每镜渲染产物
│   │   ├── first-frame.png     # 首帧静照（生成或素材裁切）
│   │   ├── last-frame.png      # 尾帧静照
│   │   ├── gen-run-v01.mp4     # aigc-video-gen i2v 产物
│   │   └ettings.log
│   │   └ulti-best.mp4          # best_image_selector 胜出（多候选时）
├── audio/
│   ├── narration.mp3           # awk-tts 旁白
│   ├── bgm.mp3                 # BGM（pexels/pixabay 或素材库）
│   ├── subtitles.srt           # 字幕
├── artifacts/                  # Stage 12 按镜顺序的最终段
│   ├── 01_*.mp4
│   └ NN_*.mp4
├── video.mp4                   # Stage 12 拼接成片
├── review/                     # Stage 13 公共 video-review 产物
│   ├── verdict.json
│   ├── frames/
├── cover.jpg                   # Stage 14 封面
└── final-deliver.md            # Stage 14 交付清单
```

### 6.5 脚本清单（全部 wrapper 模式 + python 调脚本模式）

按 AGENTS.md 调研文档"skill 已经全面实施 wrapper 模式"原则 + "涉及 python 的必须制作脚本，以 `python /path/to/script.py` 模式调用"。本技能脚本组织：

| 调用形态 | wrapper（薄转发） | 内部脚本 | 用途 |
|---------|------------------|---------|------|
| `video-producer <子命令> [参数...]` | `video-producer.sh` | `scripts/<子命令>.py` | 各阶段原子能力，agent 按 SKILL.md 工作流逐个调 |

子命令首版清单（每个是 `scripts/` 下一个 .py）：

| 子命令 | 入 | 出 | 用途 |
|--------|----|----|------|
| `intent-router` | brief.md（用户给的主题/关键词，或 main 喂的 viral-chaser 报告） | `script/intent.json`（档位 + 主题） | Stage 0：把意图路由成 narrative/motion/montage 三档 |
| `reference-concepts` | viral-chaser 报告（main 喂入，可选） | `reference-driven/concepts.md`（2–3 差异化概念 + 成本 + 备选路径） | Stage 1：**只吃报告出概念**，不做下载/转写/抽帧；无报告则跳过本阶段直入 Stage 2 |
| `story-develop` | intent.json | `script/story.md` + `script/budget.json`（estimate） | Stage 2 |
| `script-write` | story.md | `script/script.md`（含 enhancement_cues + delivery_cues） | Stage 3 |
| `script-self-eval` | script.md | `script/self-eval.json`（N 维打分，任一维 <3 必返工） | Stage 3 自评 |
| `storyboard-build` | script.md | `storyboard/storyboard.json` | Stage 4 |
| `shot-decompose` | storyboard.json | `storyboard/shot_decompose.json`（每镜首尾帧+运动+variation_type） | Stage 5 |
| `character-register` | storyboard.json + 人物描述 | `characters/registry.json` + 三视图 PNG | Stage 6（三视图调 siliconflow-img-gen） |
| `slot-plan` | storyboard.json + tone | `slots/slot-plan.json` | Stage 7 |
| `asset-resolve` | slot-plan.json | `slots/asset-resolve.json`（含 rejected_picks） + 素材落 `raw_materials/` | Stage 8（调 pexels-footage / pixabay-footage / aigc-video-gen） |
| `slideshow-risk` | storyboard.json + slot-plan.json + asset-resolve.json | `slots/slideshow-risk.json`（六维分） | Stage 9（pre-compose 闸门） |
| `delivery-promise-lock` | storyboard.json + brief.md | `slots/delivery-promise.json`（八类锁） | Stage 9 |
| `render-shot` | shot_decompose.json + characters/ + slot-picks | `render/shot-NN/` 下产物 | Stage 10（调 aigc-video-gen i2v / siliconflow-img-gen） |
| `mix-audio` | script.md（delivery_cues）+ video.mp4 | `audio/narration.mp3` + `audio/bgm.mp3` + `audio/subtitles.srt` | Stage 11（调 awk-tts + audio-mix） |
| `assemble` | render/ 顺序 + audio/ + slots/promise | `video.mp4` | Stage 12（ffmpeg concat + xfade 转场 + 烧字幕） |
| `motion-audit` | video.mp4 + delivery-promise.json | `review/motion-audit.json`（motion_led 抽查） | Stage 13 CP 侧补公共 video-review |
| `make-cover` | brief.md（标题）+ storyboard 关键帧 | `cover.jpg` | Stage 14（调 siliconflow-img-gen） |

> wrapper `video-producer.sh` 内部 `exec python3 "$SCRIPT_DIR/scripts/$1.py" "${@:2}"`——子命令名即脚本名，零路径拼接。

### 6.6 强制闸门与护栏

按 §8.4 #37 / #38 / #41 / #42 落地：

- **GATE A**（Stage 6 后）：文本产物全齐（脚本+分镜+机位+角色），**停下发用户审**，呈交摘要后**结束本轮回复**，不许同条回复进 Stage 7。批准逐闸门——早先的"你继续"不覆盖本闸门
- **GATE B**（Stage 9 后）：素材齐 + 计划过 slideshow_risk + delivery_promise 锁，**停下发用户看 contact sheet**，同上
- **返工上限**：每阶段最多返工 3 次；全片最多 3 次 send-back；每阶段 wall-time 默认上限 20 分钟（agent 卡住要报，不要反复撞）
- **不许声称没做过的事**：没有 tool result 或产物文件证明，不许声称已渲染/已生成/已改动
- **模糊意图不算确认**：用户说"做个短片""帮我策划"不算确认，必须先问清楚走哪条 workflow（narrative/motion/montage）、时长、受众；起草脚本属对话协助不许调 render 工具
- **默认小规模**：idea2video 默认 1 场 3–5 镜，不许把模糊想法擅自扩成多场多镜；用户要扩才扩
- **预算四步全量**：每阶段开头 `budget.json` 写 estimate，调任何付费生成前 reserve（锁额），调后写 actual，最后 reconcile；单动作超 $0.50 暂停确认；总额默认上限 $10，超也暂停
- **决策审计链**：每个选择（路径/模型/风格/音色/任何 fallback）记 备选 + 置信度 + 理由，跨阶段累积进 `decisions.json`

### 6.7 不写的（防越界）

- 不在 SKILL.md 里写调研结论 / MoneyPrinterTurbo / OpenMontage / ViMax / HyperFrames / html-video 字样——crew 不需要知道出处（调研文档 §5 强制）
- 不抽 `video-cover-gen` 公共 skill——封面走 `siliconflow-img-gen` + `make-cover` 子命令（调研文档 §4.7）
- 不引状态机脚本——`artifact-file-as-checkpoint` 已够（调研文档 §4.5）
- 不引 CLIP / torch 系——Fast path 走人核缩略图（§9.3 决策 3）
- 不扩图库源——Pexels + Pixabay（§9.3 决策 4）
- 不相机位树转场取帧法——首版判 C，机位连续性退化成"父机位首帧编辑重绘"（§9.3 决策 2 用户追问的答复）
- 不集成 HyperFrames / Remotion 渲染引擎——CP 视频出片走 AIGC（aigc-video-gen）+ ffmpeg，不走 HTML→MP4 引擎路径（html-video 已从 CP 移除）
- 不做批量生成（`video_count`）——CP 逐条精做，不批量撞运气（调研文档 §8.7）

---

## 7. CP 工作区其他定义文档同步更新

调研文档用户批示："workspace 下其他定义文档也要对应更新。"

### 7.1 SOUL.md

现文 §"职责边界"写的是：
- ✅ 视频生产：content-graph 生成、模板选择、素材获取、TTS、渲染、组装、去口误、高光剪辑
- ❌ 脚本创作：脚本由 main agent 或用户提供，content-producer 不负责创作

**与调研文档 §1.1 直接冲突**——CP 独占出脚本，main agent 不出脚本。去口误/高光剪辑也已划归 main（talking-head-cut / video-edit），不再属 CP。

改写为：

```
## 职责边界
- ✅ 端到端视频制作：出脚本、分镜、机位一致性、素材匹配、渲染、自检、交付（video-producer）
- ✅ 视觉拼贴动画：一句口播压成纸拼贴 B-roll（collage-broll）
- ✅ 技术演示动画：Manim 科学动画（manim-explainer）
- ✅ 平面设计全案：网页/落地页/APP 界面/品牌视觉体系（design-full）
- ❌ 平台运营 / 发布：归 main agent 的各 publish 技能
- ❌ 基于已有素材的轻剪辑（去口气词/高光剪辑/拼接/烧字幕）：归 main agent 的 video-edit / talking-head-cut
- ❌ 内容选题 / 发布策略：归 main agent
```

§"Edge Cases" 第 3 条"未提供脚本且非 ui-demo/de-mouth → 告知需要脚本，或建议通过 main agent 的 video-product 技能"——已失效（video-product 早拆，ui-demo 移 main，de-mouth 移 main）。删该条或改为"未提供脚本也不愿出脚本的视频需求 → 转 main 的 video-edit 走已有素材加工"。

### 7.2 IDENTITY.md

现文 §"Role" 写："承担视频生产与视觉设计两条线的执行：视频生产（content-graph / 模板 / TTS / 渲染 / 组装 / 去口误 / 高光剪辑）+ 视觉设计（品牌设计系统 / 网页落地页 / APP / 组件视觉）。"

同 SOUL.md 问题——"content-graph / 模板"是已移除的 html-video 范畴，"去口误 / 高光剪辑"已移 main。改写：

```
## Role
专业内容制作者，main agent 的助手。承担四条能力方向的执行：
端到端视频制作（出脚本/分镜/渲染/组装/交付）+ 视觉拼贴动画 + 技术演示动画 + 平面设计全案。
既接受 main agent 在工作流中下发任务，也接受用户直接对话。
```

> 仅此 Role 段改写；Name / 形象类型 / 性格基调 / emoji / 头像四项保持不变（调研文档 §AGENTS.md 规范：IDENTITY.md 仅此四项）。

### 7.3 MEMORY.md

现文是占位模板（用户偏好/已制作视频记录两条空表）。结构保留，但补一条"四条能力方向"提示，让 CP 启动后能立刻自知：

```
## 我的能力方向（启动自查）

content-producer 共四条能力方向，每接到活儿先按 AGENTS.md 路由表选一条：
1. video-producer — 端到端视频制作（主）
2. collage-broll — 纸拼贴组装动画
3. manim-explainer — 技术演示视频
4. design-full — 平面设计全案

## 用户偏好与设置
（首次使用后由 content-producer 在此记录用户的偏好设置）
- 默认语言：（待记录）
- 默认视频风格：（待记录）
- 默认时长目标：（待记录）
- 常用发布平台：（待记录）

## 已制作视频记录
（由 content-producer 维护）
| 日期 | 主题 | 文件路径 | 发布状态 |
|------|------|----------|----------|
```

### 7.4 TOOLS.md

现文仅一行标题，无实质内容。保持不动——本机环境备忘后续由 CP 在使用中自行补（脚本路径走 wrapper 不需备忘，环境变量见各 SKILL.md 首次使用节）。

### 7.5 HEARTBEAT.md

现文"当前无定时任务"保持不变——CP 是按需触发型，本轮重构不引入心跳。

### 7.6 BUILTIN_SKILLS / DENIED_SKILLS

**BUILTIN_SKILLS** 现清单残留：`html-video` / `siliconflow-video-gen` / `siliconflow-tts` / `ui-demo` / `design-system-picker` / `init-workspace` / `manim-explainer` / `collage-broll` / `bilibili-publish`。

按本计划更新为：
- 删 `html-video`（整体从 CP 移除）
- 删 `siliconflow-video-gen`（CP 不再保留 SiliconFlow 视频生成，主链走公共 `aigc-video-gen`）
- 删 `siliconflow-tts`（已上移公共且本轮改造为 `awk-tts`，CP 不留副本）
- 删 `ui-demo`（已移 main，调研文档 §1.2）
- 删 `bilibili-publish`（平台运营归 main，调研文档 §2.1 标注"暂时调整出代码仓"）
- 删 `design-system-picker` / `init-workspace`（合并为 `design-full`）
- 加 `design-full`（新建）
- 加 `video-producer`（新建，CP 专属主技能）
- 保 `manim-explainer` / `collage-broll`

更新后清单：`video-producer` / `collage-broll` / `manim-explainer` / `design-full`。

**DENIED_SKILLS** 现清单是"main / 业务拓展 / 信息采集"三类技能的列举，与本轮重构无波及，保持不动。

### 7.7 USER.md

本文件由用户在首次使用后自行填写，本轮重构不改动其结构。仅确认文件存在且不含已失效引用。

---

## 8. 落地顺序与清理清单

### 8.1 执行顺序（每步落地后 VERIFY 再进下一步）

> 顺序设计原则：先改公共底座（CP 与 main 共享的 domain skill），再改 CP 自己的 workflow skill，最后改 CP 定义文档。避免中间态断链。

```
Phase 1  公共 domain skill 改造
  1.1  skills/siliconflow-tts → skills/awk-tts
       （§2 全清单：rename + SKILL.md rewrite + tts.py rewrite + wrapper + 引用方更新 + CP �副本删）
  1.2  skills/video-review 不动（§3 已定保留）
  VERIFY 1.1: grep 全仓无残留 'siliconflow-tts' 字样；awk-tts.sh 跑 --help 不报错；crews/main 现有 video-edit/talking-head-cut 不引错

Phase 2  CP workflow skill 调整
  2.1  整合 design-full（§5.4 全清单：design-system-picker + init-workspace + AGENTS.md 工作模式2 → design-full）
  2.2  collage-broll SKILL.md：核对 awk-tts / video-review 引用（现 collage-broll Gate3 调 aigc-video-gen 不调 TTS，但 Gate3 出片后补一道 video-review 技术自检；§2.3 改 awk-tts 不波及 collage-broll）
  2.2b manim-explainer SKILL.md：现引用 'siliconflow-tts' 改 'awk-tts'；现引用 'fragment-assembly' 改 'video-producer assemble 子命令'（fragment-assembly 是已移除的旧技能，调研文档 §2.2 未列但 CP 现清单确无）；其余保留
  2.3  新建 video-producer（§6 全清单：14 个子命令 wrapper + scripts + SKILL.md + stages/*.md + gates + 工作区约定）
  VERIFY 2.1: design-full.sh 跑通建空任务目录 + pick.sh 匹配不报错；旧 design-system-picker/init-workspace 目录已删
  VERIFY 2.3: video-producer.sh 跑 --help 列子命令；逐子命令 --help 不报错；GATE A/B 措辞在 SKILL.md 出现；artifact-file-as-checkpoint 在 SKILL.md 出现

Phase 3  CP 定义文档同步
  3.1  AGENTS.md 重构（§4.2 骨架：四能力方向路由表 + 通用约定 + 衔接关系，删工作模式2 全部细节）
  3.2  SOUL.md §7.1 改写
  3.3  IDENTITY.md §7.2 改写（仅 Role段）
  3.4  MEMORY.md §7.3 改写
  3.5  BUILTIN_SKILLS §7.6 更新
  3.6  TOOLS.md / HEARTBEAT.md / USER.md 不动（§7.4 / §7.5 / §7.7）
  VERIFY 3: AGENTS.md 路由表四行齐；SOUL/IDENTITY 无"去口误/高光剪辑/content-graph/模板"字样；BUILTIN_SKILLS 四项齐

Phase 4  全仓终检
  4.1  grep 全仓 'siliconflow-tts' / 'design-system-picker' / 'init-workspace' / 'html-video' / 'fragment-assembly' / 'video-product'（CP 侧占位）残留引用，逐处修
  4.2  git diff 自检：所有技能 SKILL.md + scripts 注释无'调研/借鉴/参考/MoneyPrinterTurbo/OpenMontage/ViMax/HyperFrames/html-video/决策 X.X/本轮/范式'等开发判断词（调研文档 §5 强制）
  4.3  各 wrapper 跑 --help 不报错
  4.4  skills/ 与 crews/*/skills/ 的 python 脚本无裸 ffmpeg/python 调用外泄（wrapper 模式 + python 走脚本模式两条强制）
```

### 8.2 删除清单（一次性 git rm）

| 路径 | 理由 |
|------|------|
| `crews/content-producer/skills/video-product/` 整目录 | 仅占位 + main 副本，video-producer 取代 |
| `crews/content-producer/skills/siliconflow-tts/` 整目录 | 已上移公共，本轮改造为 awk-tts，CP 不留副本 |
| `crews/content-producer/skills/design-system-picker/` 整目录 | 合并入 design-full |
| `crews/content-producer/skills/init-workspace/` 整目录 | 合并入 design-full |

> 删前已 git mv 资产物（design-systems / pick.sh / init.sh）到 design-full，不丢资产。

### 8.3 新建清单

| 路径 | 类型 | § |
|------|------|---|
| `skills/awk-tts/` | rename + rewrite 自 skills/siliconflow-tts | §2 |
| `crews/content-producer/skills/design-full/` | 新建（合并 design-system-picker + init-workspace + AGENTS.md 工作模式2） | §5 |
| `crews/content-producer/skills/video-producer/` | 新建（端到端主技能） | §6 |

### 8.4 改写清单（不新建不删，原地改）

| 路径 | § |
|------|---|
| `crews/content-producer/AGENTS.md` | §4.2 |
| `crews/content-producer/SOUL.md` | §7.1 |
| `crews/content-producer/IDENTITY.md` | §7.2 |
| `crews/content-producer/MEMORY.md` | §7.3 |
| `crews/content-producer/BUILTIN_SKILLS` | §7.6 |
| `crews/content-producer/skills/collage-broll/SKILL.md` | §8.1 Phase 2.2（补 video-review） |
| `crews/content-producer/skills/manim-explainer/SKILL.md` | §8.1 Phase 2.2b（siliconflow-tts → awk-tts，fragment-assembly → video-producer assemble） |
| `crews/main/skills/video-edit/SKILL.md` | §2.3 第 7 点（siliconflow-tts → awk-tts） |

---

## 9. 开放项与确认

本计划在调研文档 §9.3 七项决策已获用户批示的基础上执行，不再重新发起 request_user_input。仅下列执行期需拍板的细项留待开发中定：

| # | 细项 | 默认判 | 触发拍板时机 |
|---|------|-------|------------|
| 1 | `awk-tts` 的火山侧 voice id 列表（首版列几个、对应情绪/性别/语速） | 5 个，对齐原 siliconflow 的 benjamin/charles/claire/david/diana 风格 | Phase 1.1 写 SKILL.md 前，火山控制台实测各音色后定 |
| 2 | 中文字数预算表的具体字数档（调研文档 §8.1 #6 标"中文需按字数重标定，需实测 awk-tts 中文语速"） | 首版沿用英文 wpm 表的相对档位（contemplative ~120 / conversational ~150 / energetic ~180 / technical ~130），落地后实测修正 | Phase 2.3 写 video-producer Stage 3 stage 文时定首版，首个真实项目后实测修正 |
| 3 | tone→slot 数表中文重标定（调研文档 §8.2 #19） | 首版沿用英文纪录片语境的相对档位（挽歌 4.0s/~15、庄重 3.5s/~17、梦幻 3.0s/~20、诙谐 2.0s/~30、紧迫 1.2s/~50），落地后实测修正 | 同 #2 |
| 4 | camera_tree 转场取帧法是否引入（调研文档 §8.2 #14，用户批示追问 ffmpeg 转场） | 首版判 C 不引入，机位连续性退化成"父机位首帧编辑重绘 + Stage 12 ffmpeg xfade"；积累 5–10 个真实项目后做一次成本/收益实测再定 | Phase 2.3 按 C 落地，后续视项目量再议 |
| 5 | 阶段 wall-time 上限（调研文档 §8.4 #38，默认 20 分钟）与单动作/总额预算阈值（调研文档 §8.4 #45，默认 $0.50 / $10）是否调 | 沿用默认 | Phase 2.3 写 SKILL.md 时落地，首个真实项目后视卡点情况调 |

> 上述 5 项均有默认判，不阻塞开发启动；实测修正留到真实项目期。

---

## 10. 不在本计划范围

- main agent 侧任何技能（video-edit / talking-head-cut / ui-demo / viral-chaser / 各 publish 等）的工作流调整——调研文档 §5.5 已记 main 侧 2026-07-26 落地完毕，本轮不动 main
- `crews/main/skills/video-edit/SKILL.md` 的 `siliconflow-tts` → `awk-tts` 改写——这是 §2.3 第 7 点的引用同步，属本计划范围；但 video-edit 本身的工作流不动
- HyperFrames / Remotion / html-video 引擎路径——调研文档 §8.7 已判不吸收，CP 视频出片走 AIGC + ffmpeg
- 批量生成 / 多语言脚本 / 跨平台一键发布——调研文档 §8.7 已判不引入
- CLIP / torch 系本地模型——调研文档 §9.3 决策 3 已判不引入
- 扩充图库源（Coverr / Mixkit / Archive.org / Videvo 等）——调研文档 §9.3 决策 4 已判不扩充

---

## 11. 风险与回滚

### 11.1 风险

| 风险 | 缓解 |
|------|------|
| awk-tts 改造后火山 seed-tts-2.0 API 字段与本仓脚本假设不符 | Phase 1.1 用真实 key 跑一次端到端 curl 验证字段后再写 tts.py；保留 siliconflow-img-gen 同范式（已跑通） |
| video-producer 14 子命令首版工作量大，并行开发易冲突 | 按 §8.1 Phase 2.3 串行落地，每子命令 wrapper + scripts 单独 commit；先落 Stage 0–6（文本产物）+ GATE A，再落 Stage 7–14 |
| design-full 合并时 design-systems/ 14 套规范文件漏迁 | git mv 整目录，迁后 ls 比对文件数；index.json 内部路径如有绝对引用一并改 |
| CP 定义文档同步遗漏导致 crew 启动后误路由 | Phase 3 落地后跑一次 openclaw config-eval（或等价自检），确认 BUILTIN_SKILLS 与 skills/ 实际目录一致 |

### 11.2 回滚

每 Phase 单独 commit，回滚粒度 = 单 Phase。任一 Phase VERIFY 失败即停止不进下一 Phase，先修该 Phase。

awk-tts 改造失败回滚点：`git revert` Phase 1.1 commit，`skills/siliconflow-tts` 整目录恢复（git mv 是 reversible，未删原 commit）。

---

（计划完）
