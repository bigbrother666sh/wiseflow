# 视频号账号对标 Workflow

用于分析对标账号或一组对标视频，形成独立 DNA，并与默认或指定 DNA 逐项比较。对标样本不得直接写入 `dna-0`；用户采纳后，只有转译后的规则可融合进基线 DNA。

## 入口判断

走本 Workflow：

- “分析对标账号”
- “看看这个视频号和我们风格差异”
- “这几条高分享视频有什么共同模式”
- “建一个对标 DNA”

不走本 Workflow：

- 用户明确说“把这条视频落到某个 DNA 上” -> 走 `style-dna.md`
- 账号定位和默认 DNA 初始化 -> 走 `account-setup.md`
- 抖音 / B站 / 小红书视频的追爆拆解（只为拿拆解报告，不建对标 DNA）-> 顶层 `viral-chaser`

## 对标 DNA 选择

1. 每个对标对象或样本组使用一个独立 DNA，建议命名为 `dna-benchmark-{slug}`。
2. 同一组对标账号或视频复用同一个 DNA 并增量更新；不因每次交互重复新建。来源差异保留在 report 证据中。
3. 对标 DNA 不进入默认内容生产，除非用户明确采纳其中某些规则。
4. 用户指定比较基线时使用该 DNA；未指定时使用 `dna-0`。

## 分析流程

### Step 1 - 获取样本

视频号没有公开抓取路径，样本获取按来源处理：

| 来源 | 处理 |
| --- | --- |
| 自己账号的作品 | `wx-channel-engagement list` 拿描述文案与行内指标；完整口播仍需转写或用户提供 |
| 用户提供文字稿 / 视频文件 | 文字稿直接输入；视频文件先经顶层 `talking-head-cut` 转写 |
| 用户提供的截图 / 口述数据 | 作为数据线索保留在 report 证据中，标注来源 |
| 跨平台参考（抖音 / B站 / 小红书链接） | 顶层 `viral-chaser` 下载 + 转写 + 拆解；跨平台样本只借鉴结构，不照搬平台调性 |

选择建议：

1. 优先选择分享、评论信号强的视频；播放量只作次要参考（视频号分享权重高于点赞）。
2. 对标账号的播放、互动数据只能来自用户提供或截图；不得编造，不得把运营效果等同于内容质量。
3. 账号级对标至少收集 10 条代表性视频样本；不足 10 条时提供全部并说明数量限制。
4. 单条视频可以形成单条观察，但不得当成账号级稳定 DNA；多个样本才分析覆盖率和共性。

### Step 2 - 建立对标 DNA

对每条视频执行：

```bash
wx-channel-style-profiler report \
  --input path/to/transcript.md \
  --dna-id {benchmark-dna-id} \
  --sample-id {sample-id}
```

再执行：

```bash
wx-channel-style-profiler build --dna-id {benchmark-dna-id}
```

Agent 必须回读文字稿，补齐 report，并基于全部 report 修订：

```text
wx_channel/dna/{benchmark-dna-id}/{benchmark-dna-id}.dna.md
wx_channel/dna/{benchmark-dna-id}/{benchmark-dna-id}.template.md
```

对标 DNA template 开头两项固定为选题、标题（含封面图与描述文案）；脚本分段默认五个语义部分（钩子、共情、信任状、价值、收尾），分段数量以对对标 DNA 文档的结构结论为准；每一部分都要能从对标 DNA 文档推导。

### Step 3 - 选择比较基线

读取：

```text
wx_channel/dna/{base-dna-id}/{base-dna-id}.dna.md
wx_channel/dna/{base-dna-id}/{base-dna-id}.template.md
```

默认 `{base-dna-id}` 为 `dna-0`。若 `dna-0` 不存在，先停止比较并提示用户走 `account-setup.md` 初始化，或由用户明确指定另一个基线。

### Step 4 - 逐项比较

比较必须覆盖两层：

1. **16 维 DNA 文档**：逐个维度比较规则、证据和适用条件；封面图需比较视觉特征与 AIGC 复现要素。
2. **template**：逐项比较选题、标题（含描述文案与封面）与脚本各分段的执行方式。

每个维度和模板部分都输出四类结论：

| 类别 | 判断标准 |
| --- | --- |
| 保持 | 基线已有优势，与目标观众和商业定位一致 |
| 引入 | 对标更有效，且不冲突业务事实、合规边界和用户偏好 |
| 局部借鉴 | 只适合钩子、文案、结构、收尾等局部场景 |
| 不采纳 | 仅依赖孤例、冲突商业定位、风险高或难稳定执行 |

每项至少说明：

1. 基线 DNA 的规则和证据。
2. 对标 DNA 的规则和证据。
3. 差异原因或适用条件。
4. 是否建议更新基线。

视频号特有比较点：社交推荐触发设计（转发动机是否明确）、前 3 秒钩子强度、真人出镜占比、私域承接路径是否完整。

### Step 5 - 采纳与更新

对比结果不自动更新基线 DNA。用户明确采纳后，选择一种方式：

1. **局部 DNA 融合**：用户决定采纳对标 DNA 的某个维度或模板部分时，直接读取对标 DNA 文档 / template 中对应内容，把它当作用户提供的一条融合要求，更新基线 DNA；不需要重新抓取参考视频，也不需要重新生成对标视频的基线 report。
2. **局部样本借鉴**：仅在用户明确希望引入原文证据、权重或 focus 时，才将对标视频重新生成属于基线 DNA 的 report，并用 `--focus` 限定采纳维度。
3. **偏好转译**：用户表达“钩子再冲突一点”“口播更生活化”等要求时，按 `style-dna.md` 的用户输入转译更新，并落到 template 的具体执行字段。
4. **明确不改 DNA**：仅作为本次选题或创作参考，不落盘到 DNA。

局部 DNA 融合流程：

1. 明确采纳范围：16 维中的维度、模板中的部分，或两者组合。
2. 读取对标 DNA 文档 / template 的对应规则、适用条件和例外。
3. 将其整理为一条可转译的输入，必须包含来源 `dna-id`、采纳范围和具体规则。
4. 在基线 DNA 上执行无新增样本的 update：

```bash
wx-channel-style-profiler update \
  --dna wx_channel/dna/{base-dna-id}/{base-dna-id}.dna.md \
  --template wx_channel/dna/{base-dna-id}/{base-dna-id}.template.md \
  --user-input "采纳 {benchmark-dna-id} 的钩子部分：xxx"
```

5. Agent 把该输入视作用户提供的参考要求，转译为基线 DNA 的 affected dimensions、聚合结论、创作规则和 template 执行字段。
6. 融合时必须检查与基线证据、业务事实、合规边界和用户偏好的冲突；冲突保留说明，不静默覆盖。

更新后必须同步修订基线 DNA 文档与 template，并保留来源说明。

对标分析的过程记录（样本清单、数据线索来源、比较结论）落盘 `wx_channel/calibration/`，供后续复盘引用。
