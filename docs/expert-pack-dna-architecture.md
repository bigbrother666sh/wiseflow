# 专家包（Expert Pack）+ DNA 架构规划

> 日期：2026-08-14；2026-08-18 更新 DNA 生产模式与跨平台 profiler 规范；2026-08-20 明确跨平台 DNA 维度边界与 template 通用开头
> 分析基准：内置 openclaw `v2026.7.1`（commit `2d2ddc43`）
> 目标版本：`v2026.7.1-2`（commit `0790d9f`，待网络可用后升级）
> 首个改造对象：`crews/main`（小贝 / main agent）

---

## 1. 背景与问题

当前每个 crew 的 workspace 沿用 OpenClaw 标准结构：`AGENTS.md` / `SOUL.md` / `TOOLS.md` / `IDENTITY.md` / `USER.md` / `HEARTBEAT.md` / `MEMORY.md` 等文件在 agent 启动时整体注入系统提示。随着 main agent 承担的工作越来越丰富（新媒体运营、BD、IR、crew 管理），`AGENTS.md` 被迫承载越来越多互相独立的流程与细则：

- `crews/main/AGENTS.md` 目前约 257 行 / 19,094 字符，已逼近单文件注入预算（默认 20,000 字符）。
- 微信公众号、小红书、抖音、视频号等平台流程差异大，但共性要求（品牌、红线、素材治理）又被重复书写。
- 不同「运营风格 / 方案」（如政务发布型公众号 vs 产品推广型公众号）无法结构化复用。
- 全量注入的细则会互相干扰，且每轮都消耗 token。

### 目标形态

```
一个 crew =
  薄 AGENTS.md（通用准则 + 专家包路由）
  + 多套专家包（工作流 + 技能组合 + 知识库 + DNA）
  + DNA 库（report 聚合 -> DNA 文档 -> DNA template）
  + 共享的 SOUL / TOOLS / IDENTITY / USER / MEMORY（人格与记忆不拆分）
```

同一个 crew 保持一个 workspace、一套记忆、一个人格；专家包只是「工作面」，不是子 crew。

---

## 2. OpenClaw 架构事实（源码结论）

以下结论基于本地 `openclaw` @ `2d2ddc43` 源码。`v2026.7.1-2` 与 `2026.7.1` 为同 minor 的 patch 版本，以下加载机制预计无实质差异；升级后需复核章节 8 的核对点。

### 2.1 Workspace Bootstrap 文件：每轮整体注入，不适合承载专家包

- 源码：`openclaw/src/agents/workspace.ts`、`openclaw/src/agents/bootstrap-files.ts`
- OpenClaw 只识别一组固定 basename：`AGENTS.md`、`SOUL.md`、`TOOLS.md`、`IDENTITY.md`、`USER.md`、`HEARTBEAT.md`、`BOOTSTRAP.md`、`MEMORY.md`。
- 默认 `contextInjection = "always"`：这些文件**每轮对话都全量注入**系统提示。
- 注入预算：单文件默认 20,000 字符（`bootstrapMaxChars`），合计默认 150,000 字符（`bootstrapTotalMaxChars`）。
- 子 agent / cron 会话会按 allowlist 过滤（例如子 agent 只保留 `AGENTS.md` + `TOOLS.md`）。

**推论**：把各平台的详细流程全部放进 `AGENTS.md`（或通过额外注入机制塞进启动上下文）会持续放大 token 消耗并加剧干扰，与「按需加载」的目标相反。

### 2.2 `bootstrap-extra-files` hook：能加载子目录 AGENTS.md，但仍是每轮全量注入

- 源码：`openclaw/src/hooks/bundled/bootstrap-extra-files/handler.ts`、`openclaw/src/agents/workspace.ts` 的 `loadExtraBootstrapFilesWithDiagnostics`
- 该 hook 支持在 `openclaw.json` 配置 glob（如 `experts/**/AGENTS.md`），把 workspace 子目录中的额外 `AGENTS.md` / `TOOLS.md` 等追加进启动上下文。
- 两个硬限制：
  1. basename 必须在标准白名单内（必须是 `AGENTS.md` 等固定文件名）；
  2. 命中的文件会随 bootstrap **每轮整体注入**，没有「这个任务才加载」的语义。

**推论**：该机制适合放「少量、跨任务必须常驻」的补充规则（如品牌红线），**不适合**承载平台级专家包。

### 2.3 项目上下文加载：只走祖先链，不会自动发现任意子目录

- 源码：`openclaw/src/agents/sessions/resource-loader.ts` 的 `loadProjectContextFiles`
- 从当前工作目录向上逐级查找 `AGENTS.md` / `CLAUDE.md`，是「祖先链」语义，不是「按主题发现任意后代目录」。

**推论**：在 `crews/main/experts/wx-mp/AGENTS.md` 写专家规则，OpenClaw 不会自动加载它；除非 agent 被明确指示去读，或该目录恰好被 2.2 的 glob 命中（又回到全量注入）。

### 2.4 Skill 机制：原生的「按需加载」通道（关键结论）

- 源码：`openclaw/src/skills/loading/skill-contract.ts`、`openclaw/src/agents/system-prompt.ts`（`buildSkillsSection`）
- 系统提示中的 `<available_skills>` 块**只注入每个 skill 的 `name` + `description` + `SKILL.md` 路径**，不注入正文。
- 系统提示明确指示：任务匹配某个 skill 时，才用 read 工具读取其 `SKILL.md` 全文并遵循。
- 默认预算：最多 150 个 skill 进入提示、合计 18,000 字符；单个 `SKILL.md` 磁盘读取上限 256KB。
- `SKILL.md` 所在目录即「skill root」：目录内可以自由放 `workflow.md`、`knowledge/`、`dna/`、`scripts/` 等附属文件，由 agent 在读入 `SKILL.md` 后按需二次读取。

**推论**：**专家包应实现为一个 skill 目录**。`SKILL.md` 作为专家包入口（对应你说的每个工作内容的「agents.md」），平台细则、知识库、DNA 都作为包内附属文件按需读取。这是 OpenClaw 原生支持、零代码改动的按需加载路径。

### 2.5 技能可见性控制

- 源码：`openclaw/src/skills/loading/workspace.ts`（`skillFilter`）、`openclaw/src/config/sessions/types.ts`
- 每个 agent 可通过 `agents.list[].skills` 配置可见技能白名单；`BUILTIN_SKILLS` / `DENIED_SKILLS`（本仓约定）在部署脚本中折算到该配置。
- 本仓部署：`crews/main/skills/*/` 由 `scripts/lib/crew-workspaces.sh` 软链到 `~/.openclaw/workspace-main/skills/`，改仓内文件即时生效。

**推论**：专家包放进 `crews/main/skills/expert-<domain>/` 即可自动进入技能发现与 allowlist 体系，无需新部署机制。

---

## 3. 可行性结论

**方案可行，且大部分能力是现成的**，但要做两个关键取舍：

| 设想 | 结论 | 原因 |
|------|------|------|
| 薄 `AGENTS.md` + 按工作内容加载细则 | ✅ 直接可行 | 细则迁入专家包 `SKILL.md`，复用原生按需读取 |
| 每个专家包单独一个 `agents.md` 并自动加载 | ⚠️ 不建议 | OpenClaw 不自动加载任意子目录 `AGENTS.md`；`bootstrap-extra-files` 会变成每轮全量注入 |
| 专家包携带技能组合、知识库 | ✅ 直接可行 | skill 目录可包含任意附属文件；领域专属技能整体收纳进包内 `tools/`，跨领域技能保持顶层 |
| DNA ID 管理 + 三层生产 | ✅ 可行（约定层实现） | OpenClaw 不理解「DNA」语义；由 style-profiler 约定 report / DNA 文档 / template 的文件关系 |
| 共享一个 workspace / 记忆 / 人格 | ✅ 符合现状 | 专家包只是技能目录，不引入新 agent / 新 workspace |
| 从样本生成 DNA report scaffold | ✅ 可行 | 脚本负责样本记账与统计底座；定性提取必须由 Agent 回读原文完成 |

核心设计原则：**不要发明新的加载机制，把专家包做成「一等公民 skill」**。专家包同时承担两个职责：

1. **编排**：调用跨领域复用的顶层技能（打分、记录、素材采集等）；
2. **收纳**：把只服务本领域的专属技能整体挪进包内，使其从 `<available_skills>` 路由面消失。

只做编排不做收纳，会让技能数随领域数线性增长，重新制造臃肿与误路由问题。

---

## 4. 目标结构

### 4.1 目录布局（以 main crew 为例）

```
crews/main/
  AGENTS.md                      # 薄化：通用准则 + 专家包路由表（目标 < 120 行）
  SOUL.md / TOOLS.md / IDENTITY.md / USER.md / MEMORY.md   # 不变
  dna/                           # Workspace 运行时 DNA，统一按平台分目录
    wx_mp/
      {dna-id}/
        reports/
          {sample-id}.report.md
        {dna-id}.dna.md
        {dna-id}.template.md
  skills/
    expert-wx-mp/                # 专家包：微信公众号运营
      SKILL.md                   # 第一层：专家身份 + 交互原则 + 平台速查 + workflow 清单 + 工具清单
      workflows/                 # 第二层：按场景拆分的操作流程
        style-dna.md                    - DNA report 生成、聚合与 template 使用
        content-production.md           — 内容生产 SOP（想法/参考/草稿输入分支 + 长文/小绿书产出分支）
        account-setup.md                — 起号/定位/账号诊断
        account-benchmark.md            — 账号对标分析
        editing.md                      — 改稿/润色/换风格/换排版
        review.md                       — 数据复盘/对标分析
      tools/                     # 领域专属工具（被收纳的原子技能）
        wechat-style-profiler/   #   单篇 report -> DNA 文档 -> DNA template
        generate-wenyan-theme/   #   排版主题生成
        wx-mp-publisher/         #   发布到草稿箱
        wx-mp-engagement/        #   数据抓取
    expert-xhs/                  # 其他平台专家包（同结构）
    expert-douyin/
    expert-wx-channel/
    wx-mp-hunter/                # 保留顶层：跨工作流复用（对标采集）
    content-calibrator/          # 保留顶层：跨平台打分
    published-track/             # 保留顶层：跨平台发布记录
```

命名约定：

- 专家包统一加 `expert-` 前缀，与「操作型技能」（如 `douyin-publish`）区分。
- 专家包内不使用 `AGENTS.md` 作为文件名（避免与 workspace bootstrap 文件混淆，也避免被误解为会被自动注入）。
- 专家包内不保存可变 DNA。运行期生成的 DNA report、DNA 文档和 DNA template 一律写入 Workspace 的 `dna/<platform>/<dna-id>/`；专家包只保留方法论、框架和工具。

### 4.2 专家包与运行时资产分层原则

专家包是随代码部署的**能力包**，Workspace 是运行期产生的**数据区**。两者必须分开管理，不再把专家包、workflow、DNA 混称为同一个三层结构。

#### 专家包：稳定能力

```text
expert-<platform>/
  SKILL.md
  workflows/
  tools/
```

| 组件 | 职责 | 边界 |
|------|------|------|
| `SKILL.md` | 专家包入口：平台能力边界、workflow 清单、工具清单、平台速查、硬性红线 | 不承载人设、通用准则或完整操作步骤；这些分别属于 crew 层文件和 workflow |
| `workflows/*.md` | 场景编排：决定何时用哪个工具、何时由 Agent 分析、何时写入运行时资产 | 只写流程和调用关系，不实现具体工具逻辑 |
| `tools/*` | 原子能力：profiler、选题、写作、排版、发布、取数等工具 | 每个平台必须有同构 `<platform>-style-profiler`；工具文档只写自己的输入、输出和调用方式 |
| tool 内 `references/` | 方法论、分析框架、输出格式说明 | 附属于具体工具，不独立成全局 knowledge 层，也不保存生成数据 |

#### Workspace：运行时数据

```text
Workspace/
  dna/<platform>/<dna-id>/
    reports/{sample-id}.report.md
    {dna-id}.dna.md
    {dna-id}.template.md
  wenyan-theme/                 # 平台排版主题
  calibration/<platform>/       # 平台校准与复盘数据
```

| 数据 | 归属 |
|------|------|
| DNA report / DNA 文档 / DNA template | `dna/<platform>/<dna-id>/` |
| 排版主题 | 平台主题目录，例如 `wenyan-theme/` |
| 校准、复盘、抓取结果 | 对应平台运行时数据目录 |

硬性边界：

1. 专家包可部署、可替换、可重建；运行期写入只能发生在 Workspace。
2. DNA 不是专家包内置知识，而是由 style-profiler 生成并持续更新的运行时资产。
3. 不单独设全局 knowledge 层；方法论文档必须附属于具体 tool 或 workflow。
4. workflow 负责编排，tool 负责操作，Workspace 负责保存生成物。

### workflow 设计原则

**workflow 必须基于工具**，每一步操作都要能落到具体工具上，不能凭空写"专家来分析"、"专家来判断"。

- 能用工具的用工具（style-profiler / publisher / hunter / calibrator 等）
- 必须靠 agent 判断的，明确写"agent 推理/分析"（如数据诊断、选题价值判断）
- 严禁出现模糊的"专家进行 XX"这种步骤——要么有工具，要么明确是推理任务
- 工具调用关系写进 workflow，不写进每个工具的 SKILL.md（工具文档只写自己的输入输出）
- 至少包含如下6个 workflow——`style-dna`（DNA 创建与更新）、`content-production`（内容生产，含仿照创作、用户输入草稿等输入分支）、`account-setup`（起号与定位）、`account-benchmark`（对标比较）、`editing`（改稿与调整）、`review`（数据复盘）

### 4.3 编排与收纳的判定规则

只被一个领域使用的技能必须收纳；被多个工作流复用的技能保持顶层。判定规则只有一条：

收纳后的工具 SKILL.md 要**瘦身**：
- 去掉"当用户说 XX 时触发本技能"这类触发语——它不再是独立技能了
- 去掉"与其他技能的衔接 / 上下游"——衔接关系写进 workflow，不写在工具文档里
- 只保留：工具用途、输入是什么、输出是什么、怎么调用、注意事项
- 语气从"我是一个技能"改成"这是一个工具说明书"

| 技能使用范围 | 处理方式 | 示例 |
|--------------|----------|------|
| 跨领域复用 | 保持顶层技能，专家包编排调用 | `wx-mp-hunter`、`content-calibrator`、`published-track`、`generate-wenyan-theme` |
| 仅服务单一领域 | 整体迁入对应专家包 `tools/`，从路由面消失 | `wx-mp-publisher`、`wx-mp-engagement` -> `expert-wx-mp/tools/` |

收纳的技术依据（源码已验证）：workspace 技能扫描器发现某目录含 `SKILL.md` 后，将其注册为一个技能即停止深入（`openclaw/src/skills/loading/workspace.ts`，`skillMd` 存在时 push 后 `continue`）。因此 `expert-wx-mp/tools/wx-mp-publisher/SKILL.md` 不会被注册为独立技能，只会作为包内说明书被按需读取。

收纳的收益：

- **技能总数不增反降**：公众号域 3 个候选（hunter/publisher/engagement）变为 2 个（expert-wx-mp + wx-mp-hunter）；小红书、抖音做同样收纳后，总技能数明显缩减。
- **路由更准**：`<available_skills>` 候选更少、区分度更高；被收纳技能的触发词（「发布公众号」「公众号留言互动」）并入专家包 description。
- **不冲突**：agent 触发 `expert-wx-mp` 后读取包内 Tool 说明属于普通文件读取，不参与技能选择，符合「一次最多选一个 skill」的提示规则。

### 4.4 薄 `AGENTS.md` 的职责边界

只保留三类内容：

1. **通用准则**：品牌红线、素材治理、记忆更新策略、跨平台一致性。
2. **专家包路由表**：任务特征 -> 专家包名的映射，例如：

   | 任务特征 | 先读 |
   |----------|------|
   | 微信公众号选题/写作/排版/发布/复盘 | `expert-wx-mp` |
   | 小红书图文/账号运营/对标 | `expert-xhs` |
   | 抖音短视频账号运营 | `expert-douyin` |
   | 视频号运营 | `expert-wx-channel` |
   | 商务拓展（BD） | （后续拆出 `expert-bd`） |
   | 投资人关系（IR） | （后续拆出 `expert-ir`） |

3. **兜底规则**：找不到专家包时的行为（询问用户 / 保守处理 / 不猜测 DNA）。

迁出内容：各平台的具体流程、注意事项、文件命名规范、打分细节、发布步骤，全部下沉到对应专家包。

### 4.5 专家包 `SKILL.md` 模板

见已经完成的 `crews/main/skills/expert-wx-mp`

### 4.6 DNA 定义与生产模式

DNA 是一个以 `dna-id` 为管理主体的内容生产规则集。它不按账号名建模：一个 DNA 可以持续吸收任意数量的文章，样本可以来自一个账号，也可以来自多个账号不同的文章，甚至来自用户直接的想法；是否归入同一个 DNA，取决于用户指定（未指定，均录入默认的 `dna-0`)

DNA 的生产必须是三层产物：

```text
单篇文章 -> DNA report
同一个 DNA 目录下的全部 report + 权重/focus + 用户输入转译 -> DNA 文档
DNA 文档 -> DNA template
```

#### 4.6.1 存储结构

运行时统一保存在 Workspace 根目录，按平台和 DNA ID 分层：

```text
dna/<platform>/<dna-id>/
  reports/
    {sample-id}.report.md
  covers/
    {sample-id}.{ext}
  {dna-id}.dna.md
  {dna-id}.template.md
```

以微信公众号为例：

```text
dna/wx_mp/{dna-id}/reports/{sample-id}.report.md
dna/wx_mp/{dna-id}/covers/{sample-id}.{ext}
dna/wx_mp/{dna-id}/{dna-id}.dna.md
dna/wx_mp/{dna-id}/{dna-id}.template.md
```

硬性边界：

1. DNA report 必须归属于一个 `dna-id`，build/update 时拒绝混入其他 DNA 的 report。
2. 原始文章可临时来自任意位置；生成后的 report 必须进入该 DNA 的 `reports/`。
3. 专家包内只保留工具、方法论和框架，不保存可变 DNA。

#### 4.6.2 DNA report

DNA report 是单篇作品的定性提取结果，不是账号级结论，也不是写作模板。每篇 report 记录：

- 平台维度（微信公众号当前为 17 维）的单篇结论；
- 原文证据；
- 可复用创作信号；
- 聚合权重，默认 `1`；
- focus，限制该篇只影响某些维度；
- 来源路径；
- 可选的封面图等视觉素材路径；视觉特征必须由视觉模型分析，并能反推为 AIGC 生成要素。

单篇 report 不负责判断跨篇稳定性。是否成为共性、偏好、孤例或例外，由 DNA 文档聚合阶段判断。

#### 4.6.3 DNA 文档

DNA 文档聚合同一个 DNA 目录下的全部 report，形成当前采用的生产规则。每个维度至少包含：

1. **聚合结论**：当前怎么选题、表达、组织或推进。
2. **报告依据**：来自哪些 report、权重和 focus。
3. **创作规则**：生产时必须怎么做。

聚合时要区分：

- 高覆盖共性；
- 高权重样本带来的偏好；
- 只在指定 focus 上借鉴的信号；
- 单篇孤例或例外；
- 用户输入转译后的规则。

无法获取表现数据时默认等权；用户可显式指定某篇权重更高，或指定只在某些维度参考该篇。

#### 4.6.4 DNA template

DNA template 是从 DNA 文档推导出的生产模板。它不是概念说明，而是写稿时直接执行的结构化要求。

通用形态：

```markdown
（选题角度推荐：xxx、xx、xxx）
（选题需考虑的受众关联角度：xxx）

[标题]（类型为主：xxx、xx、xx）
（参考：xxx、xxx、xxx）
（封面图：比例、类型与视觉重点、主体/场景……）

[起部分]
（本段用于引出话题，多用短句，从 xxx 起步……）
```

template 开头两项跨平台通用：**选题**与**标题（含封面图）**——任何平台的生产都先解决「写什么」和「怎么命名、怎么呈现封面」；第三项起由各平台从自己的 DNA 文档推导。分段数量由 DNA 文档的结构和起承转合结论决定，不固定为三段或四段。

template 必须能从 DNA 文档推导，不能引入 DNA 文档未确认的规则。

#### 4.6.5 用户输入

用户输入是参考信息，不是可直接入库的 DNA 规则。Agent 必须把用户输入转译到具体维度，例如：

```text
sentence-rhythm：提高短句比例，连续长句不超过两句
vocabulary-syntax：优先使用动词驱动的短表达
narrative-micro-operations：转折处使用一句成段强化节奏
```

DNA 文档中的用户输入转译区必须记录：

- 原始输入来源；
- affected dimensions；
- DNA 文档修改；
- template 修改；
- 处理状态。

template 只写转译后的执行规则，不直接抄用户原话。用户不需要确认后登记索引；用户意见可以直接推动 DNA 更新，但必须落为具体维度规则。

#### 4.6.6 统计边界

脚本统计只作为聚合证据底座，可用于句段、标点、人称、时长、镜头等平台相关观测，不生成总分，不决定风格是否合格。定性判断由 Agent 回读 report 与必要原文完成。

高频表达、关键词或标签只是候选线索。分词器不能直接判断口头禅、签名式表达或平台叙事特征；任何分词结果都必须经 Agent 结合原文解释后才能进入 DNA 文档。

### 4.7 跨平台 style-profiler 统一规范

每个平台专家包必须有对应的 style-profiler tool，命名建议：

```text
crews/<crew>/skills/expert-<platform>/tools/<platform>-style-profiler/
```

结构、模式、形态、流程必须与 `wechat-style-profiler` 一致：

1. **命令模式**：`report` / `build` / `update`。
2. **存储模式**：`dna/<platform>/<dna-id>/reports/`、`<dna-id>.dna.md`、`<dna-id>.template.md`。
3. **生产模式**：单篇 report -> 聚合 DNA 文档 -> 推导 DNA template。
4. **权重与 focus**：支持单篇权重和维度级 focus。
5. **用户输入**：进入转译区，由 Agent 映射到平台维度后同步 DNA 文档与 template。
6. **统计边界**：脚本只做证据底座，不评分、不替代定性判断。
7. **更新模式**：合并历史 report 与新 report，保留 Agent 已完成结论和自定义段落。
8. **template 开头两项**：template 开头两项统一为选题、标题（含封面图）；第三项起平台自定义。

各平台允许不同、且必须单独讨论的部分只有：

- DNA 提取与分析维度（可以与微信 17 维截然不同；本规范不要求其他平台采纳 17 维）；
- 维度分组和命名；
- 平台特有观测物，例如图文的标题与分段、视频的分镜与节奏、电商的卖点组织；
- template 第三项起的分段结构（开头两项固定为选题、标题（含封面图））；
- focus ID 集合。

其他平台改造固定顺序：

1. **先搭架构**：复制 wechat-style-profiler 的命令契约、存储结构、三层产物、权重/focus、用户输入转译和 update 机制，仅保留通用维度占位。
2. **再定义维度**：与用户讨论并确认该平台的 DNA 提取与分析维度；维度可以与微信截然不同，本规范不要求采纳 17 维，没有确认前不得直接照搬。
3. **最后接入工作流**：将内容生产（含仿写）、改稿等下游环节改为读取该平台 DNA template 直接执行。
4. **配齐 workflow 基线集**：每个平台的专家包至少包含与 wx_mp 对应的 6 类 workflow——`style-dna`（DNA 创建与更新）、`content-production`（内容生产，含仿写 / 改写等输入分支）、`account-setup`（起号与定位）、`account-benchmark`（对标比较）、`editing`（改稿与调整）、`review`（数据复盘）。命名可按平台语境微调，职责不能缺；平台特有场景（如 wx_mp 的小绿书）优先作为 content-production 的产出分支，确有必要才独立成 workflow。

### 4.8 Markdown 引用与运行时数据边界

后续平台改造必须遵守两条硬性边界：

1. **跨资源引用只写逻辑名称**。
   - Workflow 与 Tool 的 Markdown 示例中，引用其他 Tool / Workflow 时写资源名，例如 `wechat-style-profiler`、`Style DNA Workflow`，不写 `../tools/...`、`../workflows/...`、`tools/...`、`workflows/...`。
   - 资源名必须真实存在；引用前先确认该 Tool / Workflow 仍在专家包内，已删除的工具不得出现在示例中。
   - Agent 的默认工作目录是 Workspace，不是专家包目录。相对路径会被误解为 Workspace 路径，导致错误拼接。
   - 专家包部署时通过软链进入运行环境（见 `docs/d21-symlink-skill.md`），包内资源不会被展开到 Workspace。根 `SKILL.md` 应统一说明：Tools / Workflows / DNA 模板是逻辑资源名；只有明确声明的 Workspace 目录才按 Workspace 根解析。
   - 只有工具清单中明确列出的 wrapper 名称可以直接作为 shell 命令调用；未暴露 wrapper 的 Tool 名称仅用于定位工具说明，不得拼成脚本路径。

2. **运行期数据只能写 Workspace**。
   - DNA report、DNA 文档、DNA template、主题 CSS、抓取结果、校准数据等生成物，都必须保存到 Workspace 下的平台数据目录（例如 `dna/wx_mp/`、`wenyan-theme/`、`calibration/wx_mp/`）。
   - 不得写入专家包的 `dna/`、`references/`、`tools/` 或其他包内目录。专家包是可替换、可重建、可软链的代码与规则资产；运行期写入会造成实例状态和源仓状态耦合， reinstall / 重建 / 升级时也容易丢失。
   - 专家包只发布方法论、框架和工具；DNA 生成结果保存在 Workspace `dna/<platform>/<dna-id>/`，不通过索引登记。

---

## 5. 与现有机制的整合

### 5.1 现有内容的去向

| 现状 | 去向 |
|------|------|
| `AGENTS.md` 中各平台流程细节 | 拆进对应专家包 `workflows/*.md` |
| 各平台起号/运营知识文档 | 拆分：平台规则进 SKILL.md、操作步骤进 workflow、风格偏好进 DNA |
| 外部移植的专家 persona | 拆分：通用原则进 SKILL.md、风格调性拆成 DNA 文档、KPI 和不适用的内容删除 |
| `business_knowledge.md`（品牌与业务） | 留在 workspace 根，专家包只引用不复制 |
| `calibration/`、`campaign_assets/`（数据 / 资产） | 留在原位，专家包通过路径引用（不是知识资产，不搬家） |
| 仅限单一领域的技能 | 整体迁入对应专家包 `tools/`，同时从 `BUILTIN_SKILLS` / allowlist 移除 |
| 跨领域技能（如 `wx-mp-hunter`、`content-calibrator`、`published-track`） | 保持顶层独立技能，由专家包编排调用 |

### 5.2 不使用的机制及原因

| 机制 | 决定 | 原因 |
|------|------|------|
| `bootstrap-extra-files` glob 注入 | 不用于专家包正文 | 每轮全量注入，违背按需加载；可选择性用于极少量品牌红线补充（但建议仍留根 `AGENTS.md`） |
| 专家包子目录 `AGENTS.md` | 不使用 | 不会被自动加载，语义误导 |
| 每个专家一个子 crew / 子 workspace | 不使用 | 破坏「一个 crew 一套记忆与人格」的目标，且增加路由与管理成本 |

---

## 6. 实施路径参考

以下是 wx_mp 实战验证过的阶段拆解。

### Phase 0：盘点

- 列清单：该平台现有几个顶层技能、哪些是专属、哪些是复用
- 列清单：`AGENTS.md` 里哪些段落是这个平台的
- 列清单：knowledge / calibration / 其他地方有没有散落的平台文件
- 判断收纳对象：只有这个平台用的 → 进 tools/；多个平台用的 → 留顶层

### Phase 1：骨架 + 入口

- 建专家包骨架：`SKILL.md` + `workflows/` + `tools/`
- 写好 SKILL.md 的 description 和工具清单
- 部署验证：确认该技能出现在 `<available_skills>`、子目录 SKILL.md 不出现
- wrapper 扫描扩展：确认 `tools/` 里的 wrapper 能被 expose 出来（需要脚本支持，见下）

### Phase 2：迁移 + 收纳

- 把 AGENTS.md 里的平台流程拆进对应 workflow
- 把知识文档拆分：规则进 `SKILL.md`，步骤进 workflow，方法论附属于 tool，风格进入 Workspace DNA
- 执行技能收纳：原子技能整个目录移进 `tools/`
- 删旧位置 + 更新引用（BUILTIN_SKILLS、AGENTS.md、其他技能里的交叉引用）
- 从外部移植来的 persona：按"原则→SKILL、风格→DNA、没用的删掉"原则拆分

### Phase 3：验证 + 收口

- 跑一遍端到端：确认 workflow 链路通、工具能调、路径都对
- 薄化 AGENTS.md：删掉对应平台的细节，只留路由入口
- 残留引用检查：rg 一遍旧路径，确保没有漏网之鱼

### Phase 4：DNA 工具链 + 多平台扩展（后续）

- 每个平台专家包先落地同构 `<platform>-style-profiler`：统一 report / build / update 命令、DNA ID 存储和用户输入转译机制。
- 平台架构完成后，与用户确认该平台独有的 DNA 提取与分析维度；维度可以与微信截然不同、不必对齐 17 维，但 template 开头两项（选题、标题（含封面图））通用。
- 维度确认后再接入内容生产、改稿等下游 workflow，并配齐 4.7 要求的 6 类 workflow 基线集。
- 逐步沉淀更多 DNA：每个 DNA 持续追加 report，并通过 update 重聚合同步 DNA 文档与 template。

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 路由失败：任务描述与专家包 description 匹配不准 | 走错流程或回退到通用行为 | description 写触发词与排除项；`AGENTS.md` 路由表兜底；试点期观察误路由案例 |
| DNA 选择混乱 | 多套风格规则同时生效，输出摇摆 | 生产任务必须明确一个 `dna-id`；如需融合，先把用户输入和新样本转译进该 DNA，再重聚合并更新 template |
| 专家包膨胀为新的「小 AGENTS.md」 | 按需读取成本上升 | `SKILL.md` 只做入口与索引，细节分层到 `workflow.md` / `knowledge/` |
| 技能提示超预算（150 个 / 18k 字符） | 专家包不出现在 `<available_skills>` | 控制 description 长度；合并低频操作技能；定期审计 skill 数量 |
| 弱模型路径拼接错误 | 读不到包内文件 | 遵循 D21 wrapper 原则；包内脚本统一暴露 wrapper；`SKILL.md` 用相对路径引用 |
| 子 agent / cron 会话上下文变薄 | 专家流程在子会话不可用 | 子 agent prompt 中显式给出专家包入口路径，或由主 agent 编排后再 spawn |
| 收纳后残留引用：allowlist、脚本路径、wrapper 仍指向旧位置 | 调用失败或旧技能复活 | 迁移时同步更新 `BUILTIN_SKILLS` / `DENIED_SKILLS` / wrapper；部署后用 `openclaw skills list` 类命令核对 |

---

## 8. 升级到 v2026.7.1-2 的核对点

本次分析基于 `2026.7.1`。网络恢复后执行：

```bash
source openclaw.version
git -C openclaw fetch origin tag v2026.7.1-2 --no-tags
git -C openclaw checkout 0790d9f
```

并更新 `openclaw.version` 中的 `OPENCLAW_VERSION` / `OPENCLAW_COMMIT`。升级后只需复核：

1. `src/skills/loading/skill-contract.ts` -- `<available_skills>` 是否仍只注入元数据；
2. `src/hooks/bundled/bootstrap-extra-files/handler.ts` -- basename 白名单是否变化；
3. `src/agents/workspace.ts` -- bootstrap 文件集合与预算默认值；
4. skill 数量 / 字符上限（150 / 18,000）是否调整。

这些均为 patch 级差异的低风险核对项，预计不影响本方案结论。

---

## 9. 验收标准

- `crews/main/AGENTS.md` < 120 行且不含任何平台专属流程细节。
- 典型任务路由到正确专家包（description 承接触发词）。
- 专家包 `SKILL.md` 未被任务触发时不进入上下文（仅 name/description 常驻）。
- 被收纳技能不再出现在 `<available_skills>`；技能总数较改造前下降（净减 = 收纳数 - 1 个专家包）。
- 专家包结构清晰：`SKILL.md`（接口 + 速查）、`workflows/`（流程）、`tools/`（原子级技能）--没有独立 knowledge 层。
- 每个平台专家包至少包含 6 类 workflow：style-dna / content-production / account-setup / account-benchmark / editing / review（wx_mp 现状即此 6 个）；每个 workflow 各对应一类用户需求，互不重叠，覆盖完整，平台特有场景可按需增加。
- style-profiler 支持 `report / build / update`，并能生成 DNA 文档与 DNA template。
- DNA 存储符合 `dna/<platform>/<dna-id>/reports/`，并在 DNA 目录下交付 `.dna.md` 与 `.template.md` 两个核心文件。
- wrapper 扫描支持 `tools/` 嵌套层，收纳后的工具命令调用方式不变。
- 部署脚本（`apply-addons.sh` / `setup-crew.sh`）无需结构性改动即可安装专家包。


## 10. 案例：微信公众号专家包改造（wx_mp）

> 首个落地的专家包。2026-08-15 完成初始改造，2026-08-18 升级为三层 DNA 生产模式，2026-08-20 合并内容生产 workflow，可作为其他平台改造的参考模板。

### 10.1 改造前基线

- 顶层技能数：3 个（`wx-mp-hunter` / `wx-mp-publisher` / `wx-mp-engagement`）+ 1 个排版（`generate-wenyan-theme`）
- AGENTS.md 中公众号相关段落：约占新媒体运营章节的 40%
- 散落知识文件：`knowledge/channels-account-launch-expert/wx_mp.md`（270 行起号手册）
- 散落数据文件：`calibration/wx_mp/`（audience / benchmark / platform-state）
- 外部移植素材：一个 `expert-wx-mp/` 目录（含 1 份 persona + 5 个工具技能）

### 10.2 改造决策一览

| 决策点 | 结论 | 理由 |
|--------|------|------|
| 专家包入口 | `expert-wx-mp/SKILL.md` | 复用原生 skill 按需加载机制，零代码改动 |
| 子技能 SKILL.md | 保留但不注册（收纳在 tools/） | 扫描器遇到 SKILL.md 就停，子目录不进 available_skills |
| 知识层 | 不设独立 knowledge/ 层 | 按稳定性拆分：规则→SKILL.md、步骤→workflow、风格→DNA |
| workflow 数量 | 6 个（style-dna / content-production / account-setup / account-benchmark / editing / review） | 一个 workflow 对应一类用户需求；2026-08-20 imitation 并入 content-production（输入分支化），新增小绿书分支与 account-benchmark |
| 专属技能收纳 | 4 个在 tools/ | 原 7 个收纳；2026-08-20 移除写作三件套（topic-outline-planner / draft-writer / title-generator），生产环节改为按 DNA template 直接执行 |
| 留顶层的技能 | 1 个（wx-mp-hunter） | 跨工作流复用的对标采集 |
| 外部 persona 处理 | 拆分后删除原文件 | 原则进 SKILL、风格进 DNA、KPI/五阶段/身份描述全删 |
| calibration 数据 | 不随迁，留原位 | 是数据记录文件，不是专家知识 |
| wrapper 兼容 | 扩展 expose_skill_wrappers 扫描 tools/ 层 | 命令调用方式零变化，收纳无感 |

### 10.3 改造后的目录

```
expert-wx-mp/
  SKILL.md                          — 身份/交互/6 个 workflow/4 个工具/平台速查
  workflows/                        — 6 个场景 workflow
    style-dna.md                    - DNA report 生成、聚合与 template 使用
    content-production.md           — 内容生产 SOP（想法/参考/草稿输入分支 + 长文/小绿书产出分支；初稿后 Frontmatter → 存文件 → calibrator 质量门 → 发布+记录）
    account-setup.md                — 起号/定位/账号诊断
    account-benchmark.md            — 账号对标分析
    editing.md                      — 改稿/润色/换风格/换排版
    review.md                       — 数据复盘/对标分析
  tools/                            - 4 个被收纳的原子技能
    wechat-style-profiler/
    generate-wenyan-theme/
    wx-mp-publisher/
    wx-mp-engagement/
```

**净值变化**：顶层技能从 4 个（wx-mp-publisher / wx-mp-engagement / generate-wenyan-theme + wx-mp-hunter）变成 2 个（expert-wx-mp + wx-mp-hunter），净减 2 个路由候选。

### 10.4 踩过的坑

1. **子目录里的 SKILL.md 不会自动消失** — 必须把技能目录移进专家包的 `tools/` 下，利用"扫描器遇到 SKILL.md 就不再深入"的机制才能真正收纳。如果只是在 description 上写"这是子技能"，没用，它还是会出现在 available_skills 里。

2. **wrapper 要扩展扫描层** — 原来的 `expose_skill_wrappers` 只扫 `skills/*/<skill>.sh`，收纳后工具在 `skills/*/tools/*/` 下，脚本要加一层 glob 才能暴露到 PATH，不然命令用不了。

3. **外部移植的 persona 大部分是废的** — 身份描述、KPI 数字、五阶段工作流这些东西要么我们已有更好的，要么不适用本土情况。真有价值的只有风格描述和几条通用原则，拆完后 183 行的文档只剩 60 行 DNA + 几条补充进 SKILL.md，净减 100+ 行。

4. **calibration/ 不是知识，别乱搬** — 一开始想跟着专家包一起迁走，后来发现这是数据记录文件，content-calibrator 脚本要读的，搬了打分链路就断了。数据文件就该留在该在的地方，专家包只引用路径就行。

5. **收纳后的工具 SKILL.md 必须瘦身** — 一开始还保留着"当用户说 XX 时触发本技能"和"上下游衔接"的内容，但它已经不是独立技能了，这些话都不对了。正确做法：触发语删了，衔接关系写进 workflow，工具文档只写输入输出和怎么用。

6. **workflow 每一步都要能落到工具** — 第一版 workflow 写了很多"专家产出选题"、"专家进行分析"这种空话，后来发现每个环节其实都有对应工具（topic-outline-planner 出大纲、draft-writer 写初稿、title-generator 起标题……）。workflow 的价值是编排工具、规定顺序和确认节点，不是写一堆空话让 agent 自由发挥。后续演进（2026-08-20）：DNA template 细化到可直接执行后，写作三件套工具被移除，选题、标题、初稿由 agent 按 template 直接产出；workflow 的价值转为编排用户输入分支、确认节点和工具衔接（抓取、封面、排版、发布）。
