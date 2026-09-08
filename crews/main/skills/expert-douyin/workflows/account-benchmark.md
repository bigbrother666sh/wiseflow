# 抖音账号对标 Workflow

用于分析对标账号或一组对标视频，形成独立 DNA，并与默认或指定 DNA 逐项比较。对标样本不得直接写入 `dna-0`；用户采纳后，只有转译后的规则可融合进基线 DNA。

## 入口判断

走本 Workflow：

- "分析对标账号"
- "看看这个号和我们风格差异"
- "这几条高播放视频有什么共同模式"
- "建一个对标 DNA"

不走本 Workflow：

- 用户明确说"把这条视频落到某个 DNA 上" -> 走 `style-dna.md`
- 只拆解单条视频不做对标 -> 直接走 `viral-chaser`
- 账号定位和默认 DNA 初始化 -> 走 `account-setup.md`

## 对标 DNA 选择

1. 每个对标对象或样本组使用一个独立 DNA，建议命名为 `dna-benchmark-{slug}`。
2. 同一组对标账号或视频复用同一个 DNA 并增量更新；不因每次交互重复新建。来源差异保留在 report 证据中。
3. 对标 DNA 不进入默认内容生产，除非用户明确采纳其中某些规则。
4. 用户指定比较基线时使用该 DNA；未指定时使用 `dna-0`。

## 分析流程

### Step 1 - 获取样本

| 来源 | 工具 |
| --- | --- |
| 视频链接（对标账号代表作） | self-spawn subagent 走 `viral-chaser`（转录 + 时长 + 标题/描述 + 互动线索 + 关键帧） |
| 对标视频评论 | `douyin-comments fetch --url <视频链接>` 直接抓取（默认前 40 条热度评论；摘要落 `douyin/ref/{benchmark-dna-id}/comments/{sample-id}.comments.md`） |
| 本地文字稿 / 脚本 | 整理为 `.md` 直接输入 profiler |
| 用户提供的截图 / 数据 / 账号信息 | 作为互动信号、账号简介、发布时间与内容形式线索保留，不编造 |

选择建议：

1. 优先选择点赞、评论、分享信号强的视频；播放量只作参考之一。优先低粉高播账号的作品（内容形式更可学习）。
2. 抖音没有账号作品列表抓取工具；请用户提供对标账号的代表性视频链接，或由 `smart-search` 辅助发现候选账号后请用户确认。
3. 账号级对标至少收集 10 条代表性视频；账号可获取视频不足 10 条时，提供全部并说明数量限制。
4. 单条视频可以形成单条观察，但不得当成账号级稳定 DNA；多个样本才分析覆盖率和共性。
5. 每条样本尽量记录账号简介、发布时间、内容形式、素材来源与授权；缺失写「未观测」，不虚构。
6. 互动数据线索只说明"用户怎么投票"，不直接等于内容质量；归因前先按 `review.md` 的混杂因素清单排除账号成熟度、投流、选题热度等干扰。

### Step 2 - 建立对标 DNA

对每条视频执行：

```bash
douyin-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {benchmark-dna-id} \
  --sample-id {sample-id} \
  --cover-image path/to/frame.jpg \
  --source-url "https://www.douyin.com/video/..." \
  --output-dir douyin/dna/{benchmark-dna-id}/reports \
  --duration 89
```

再执行：

```bash
douyin-style-profiler build --dna-id {benchmark-dna-id}
```

Agent 必须回读转录原文与关键帧，补齐 report，并基于全部 report 修订：

```text
douyin/dna/{benchmark-dna-id}/{benchmark-dna-id}.dna.md
douyin/dna/{benchmark-dna-id}/{benchmark-dna-id}.template.md
```

对标 DNA template 使用 v1 账号级语义段：定位与核心传达、选题与标题包装、内容形式与发布节奏、高数据创意模式、互动与系列、制作交接与 Pipeline、口播文案 DNA。每一部分都要能从对标 DNA 文档推导。

### Step 3 - 模式分析与差异化（agent 推理）

基于对标 DNA 与样本数据，回答三个问题（不下没有证据的结论）：

1. **它为什么有效**：对标账号的高表现内容在选题、标题包装、内容形式、发布节奏、高数据创意与互动设计上有什么共性？哪些信号在多条视频中稳定出现？
2. **相对表现**：同一账号内部，哪类内容明显高于其他条（用用户提供的互动数据判断；无数据时只做内容面分析，不编数据）。
3. **差异化切入点**：我们的账号比对标强在哪、弱在哪？有哪些内容空白或人群空白可以切入？每个切入点说明依据和建议的验证方式（一条视频验证一个变量）。

评论信号：评论用 `douyin-comments` 从对标视频直接抓取，读评论动机而不是只数评论数——喜欢内容价值、喜欢人物状态、喜欢形式设定、提出具体问题、非恶意吐槽分别指向不同的可借鉴方向。抓取时逐条串行、控制总量，避免批量请求触风控。

### Step 4 - 选择比较基线

读取：

```text
douyin/dna/{base-dna-id}/{base-dna-id}.dna.md
douyin/dna/{base-dna-id}/{base-dna-id}.template.md
```

默认 `{base-dna-id}` 为 `dna-0`。若 `dna-0` 不存在，先停止比较并提示用户走 `account-setup.md` 初始化，或由用户明确指定另一个基线。

### Step 5 - 逐项比较

比较必须覆盖两层：

1. **13 维 DNA 文档**：逐个比较定位、选题、标题包装、账号简介、内容形式、发布节奏、高数据创意、视觉/声音、口播文案 DNA、互动系列与制作管线。
2. **template 语义段**：逐项比较定位与核心传达、选题与标题包装、内容形式与发布节奏、高数据创意、互动与系列、制作交接、口播文案 DNA。

每个维度和模板语义段都输出四类结论：

| 类别 | 判断标准 |
| --- | --- |
| 保持 | 基线已有优势，与目标观众和商业定位一致 |
| 引入 | 对标更有效，且不冲突业务事实、合规边界和用户偏好 |
| 局部借鉴 | 只适合选题、包装、内容形式、发布节奏、Pipeline 等局部场景 |
| 不采纳 | 仅依赖孤例、冲突商业定位、风险高或难稳定执行 |

每项至少说明：

1. 基线 DNA 的规则和证据。
2. 对标 DNA 的规则和证据。
3. 差异原因或适用条件。
4. 是否建议更新基线。

### Step 6 - 采纳与更新

对比结果不自动更新基线 DNA。用户明确采纳后，选择一种方式：

1. **局部 DNA 融合**：读取对标 DNA 文档 / template 中对应内容，把它当作用户提供的融合要求，更新基线 DNA。
2. **局部样本借鉴**：仅在用户明确希望引入原视频证据、权重或 focus 时，才将对标视频重新生成属于基线 DNA 的 report，并用 `--focus` 限定采纳维度。
3. **偏好转译**：用户表达“选题更像对标”“实拍比例提高”等要求时，按 `style-dna.md` 的用户输入转译更新。
4. **明确不改 DNA**：仅作为本次选题或制作参考，不落盘到 DNA。

局部 DNA 融合流程：

1. 明确采纳范围：13 维中的维度、template 语义段，或两者组合。
2. 读取对标 DNA 文档 / template 的对应规则、适用条件和例外。
3. 整理为一条可转译输入，包含来源 `dna-id`、采纳范围和具体规则。
4. 在基线 DNA 上执行无新增样本的 update：

```bash
douyin-style-profiler update \
  --dna douyin/dna/{base-dna-id}/{base-dna-id}.dna.md \
  --template douyin/dna/{base-dna-id}/{base-dna-id}.template.md \
  --user-input "采纳 {benchmark-dna-id} 的内容形式与发布节奏：xxx"
```

5. Agent 把该输入转译为基线 DNA 的 affected dimensions、聚合结论、创作规则和 template 执行字段。
6. 融合时检查与基线证据、业务事实、合规边界和用户偏好的冲突；冲突保留说明，不静默覆盖。

更新后同步修订基线 DNA 文档与 template，并保留来源说明。
