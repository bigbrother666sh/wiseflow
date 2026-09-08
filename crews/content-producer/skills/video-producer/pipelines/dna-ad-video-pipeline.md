# Pipeline：dna-ad-video-pipeline（影视解说 + 反转植入）

## 定位

用于生产「叙事短片前段 + 后段集中产品/服务反转」的短视频。Brief 中写：

```yaml
pipeline: dna-ad-video-pipeline
```

Brief 未写 `pipeline` 时不强制使用本 Pipeline，Content Producer 可按 `video-producer:default` 自由选择；一旦指定本 Pipeline，必须直接采用，不得替换为自创流程。

本 Pipeline 只写编排与内容套路；原子能力全部来自 `video-producer` 与公共技能，不新增脚本。

## Brief 输入契约

MainAgent 交付的 Brief 至少包含：

| 字段 | 要求 |
| --- | --- |
| platform | douyin / wx_channel / xhs 等，用于发布说明与合规边界 |
| dna_id | 使用的账号级 DNA |
| core_message | 本条必须传达的核心信息 |
| packaging_copy | 选题、观看理由、平台包装文案方向；wx_channel 为视频简介 |
| product_points | 产品/服务事实、允许讲的能力、禁用承诺；只以 Brief 为准，不内置品牌事实 |
| voiceover | 若口播文案 DNA 已启用，main 交付口播终稿 `voiceover.md`；未启用时 CP 可在 Pipeline 内写脚本 |
| source_mode | open_license_footage / user_provided / aigc / mixed |
| assets | 素材路径、来源 URL、许可证、授权确认记录 |
| form | 横竖屏、时长带、画面风格、配音/BGM 倾向；只写账号级边界，不写逐镜细节 |
| subtitle_style | 是否烧字幕、样式与安全区要求；未指定时按平台常规可读性处理 |
| environment_constraints | 可选：质量、时长、资源或交付约束；本机资源限制仍以 CP workspace `MEMORY.md` 为准 |
| variant | two_stage / concentrated_reversal，未指定时由 CP 根据素材与 Brief 选择 |
| gates | GATE A/B 批准人（用户或 main agent）；若 main 已代理批准，需写明批准范围 |
| acceptance | 交付物、验收标准、遗留问题记录要求 |

缺失关键字段时先向 Brief owner 澄清，不得自行补品牌事实、授权或许可证。

## 素材 sourcing

来源模式只允许以下四类（含混合）：

1. **open_license_footage**：使用 Brief 指定的开源/免版权片源。main 需提供本地素材或明确授权直链；CP 只做素材入库与技术处理，不做对标拆解、转写或爆款分析。必须记录原片 URL、许可证、署名要求；发布说明中如实署名。不得把“网上能下载”等同于可商用或可改编。
2. **user_provided**：用户提供现成片段。入库前记录文件参数、来源说明、授权背景；版权风险由用户确认承担，CP 只做技术处理，不做授权背书。
3. **aigc**：按 Brief 与 DNA 风格边界生成。调用公共 `aigc-video-gen`，记录 prompt、模型、生成时间与产物 metadata；发布说明按平台要求标注 AI 生成。
4. **mixed**：以上模式混合。每一段素材都必须能追溯到来源模式与授权记录。

通用入库要求：

- 每个素材通过工具校验可解码，并记录分辨率、帧率、时长、音轨。
- 建立素材清单与候选区索引；候选区文件名必须能反查源素材时间点。
- 检查素材中是否有旧品牌名、水印、URL、域名、平台标识或不可授权元素。
- 素材支撑度不足时，回到 Brief owner 处理；不得为了凑成片编造叙事。

## 叙事与植入套路

### 通用规则

- **单线目标**：主角动机一句话说清，并在片内闭环；素材支撑不了就改写，不留断头线。
- **节拍 ≤ 6**：剧情段每节拍一句，句间因果可追；段尾悬停在求助、任务、待发或冲突节点。
- **钩连句**：转生、化身、置换等转折必须用口播明写因果，并用同色、同物或同动作的画面衔接。
- **意象桥**：产品/服务段第一镜必须复用剧情核心意象；禁止用无关风景空镜硬切。
- **产品段**：3-4 句单点深打，至少覆盖 Brief 允许的 3 个功能/价值点，每点有对应画面；产品段占比 20%-26%。
- **反转点**：two_stage 变体 63%-76%；concentrated_reversal 变体 55%-65%。比例是创作约束，不是硬编码参数。
- **收束**：产品/服务段结束后立即收尾，不加无信息量的仪式句或氛围空镜。
- **合规**：正片零 URL、零域名、零联系方式；官网、仓库、价格、活动入口只进入发布说明。产品能力与承诺只讲 Brief 允许的范围，不承诺收益数字。
- **旁白语气**：除非 Brief 另有要求，使用第三人称解说体；避免问句、感叹号、第二人称和促销信号词。若口播文案 DNA 已启用，以 main 交付的 `voiceover.md` 为准。

### concentrated_reversal 变体

- 反转点之前**零产品提及**：不插 punch 句、不散落卖点、不出现品牌暗示。
- 产品/服务介绍集中在反转后的一段完成，介绍完即收尾。
- 开源免费、安装方式、活动入口等只在 Brief 要求时进入产品段口播或贴图；域名只进入发布说明。
- 可在反转瞬间使用 whoosh 等音效标记剧情→产品切换，但不得用音效替代因果衔接。

## 制作护栏

1. **规格一次锁定**：横竖屏、目标时长、分辨率与帧率由 Brief / DNA 决定。不得为了“看起来高级”擅自放大素材；需要统一规格时，先确认素材源质量和部署环境约束，再写入 timeline 计划与决策日志。
2. **帧率一致性**：混排来源素材时，先确认各段帧率；不一致必须通过 `assemble` 的归一化参数或分段预处理统一，不得把不同帧率直接 concat 后交付。输出后核对时长、音画同步与段边界。
3. **旁白排布**：使用 `mix-audio` + `narration-align` 的实测时长 / 字级时间戳排布，不用文本长度估算。每句旁白不得越过对应镜头边界；连续旁白保留呼吸间隔，累计漂移要能追溯到每段实际时长。
4. **字幕安全区**：`subtitles.srt` 必须来自对齐后的口播时间轴；烧录前检查目标画幅安全区，避免字幕落到画面中部或关键主体上。字幕样式由 Brief / DNA 的视觉边界决定，不硬编码项目个案参数。
5. **素材四查**：候选帧与成片抽帧检查 URL / 域名、旧品牌名或水印、残缺元素、字幕遮挡。发现风险优先换干净素材窗口；裁切只能作为确认安全后的次选。
6. **AIGC 原声**：AIGC 声画同出素材如含有效环境音，可作为低音量音床并在口播下 ducking；无有效音轨时补静音，不用噪声填充。
7. **决策审计**：素材取舍、规格、音色、字幕样式、fallback 与弃用中间产物都写入 `script/decisions.json` 或 `final-deliver.md`，不留在口头说明。

## 原子能力映射

| Pipeline 环节 | 使用能力 |
| --- | --- |
| Brief 解析与决策审计 | Agent 读取 Brief；决策写 `script/decisions.json` |
| 口播/脚本 | main 交付 `voiceover.md` 时，原样落为 `script/script.md` 并锁定，不重写策略文案，仍跑 `script-self-eval` 做检查；未交付时用 `story-develop` → `script-write` → `script-self-eval` |
| 分镜与素材 slot | `storyboard-build` → `shot-decompose` → `slot-plan` |
| 素材获取 | `asset-resolve`（stock/AIGC slot）或按 Brief 素材清单入库；AIGC 段用 `render-shot` |
| 口播与字幕 | `mix-audio`；需要逐句对齐时 `narration-align` |
| 字幕烧录 | 使用已暴露的字幕原子命令（当前为 `video-edit subtitles`）；不可用时向 Brief owner 报工具缺口，不手写 ffmpeg |
| 闸门前评估 | `slideshow-risk` → `delivery-promise-lock` |
| 切段与时间轴 | `clip-trim` / `timeline-compose` |
| 混音 | `audio-mix`；环境音、口播、BGM、音效按 Brief 与素材音轨处理 |
| 合成 | `assemble`；需要分段预合时 `scene-compose` |
| 动效审计 | `motion-audit` |
| 技术自检 | 公共 `video-review` |
| 封面 | `make-cover`，封面主文案与视觉承诺来自 Brief/DNA；wx_channel 无平台标题，封面主文案用核心传达 |
| 交付 | `final-deliver.md` |

禁止直接手写 ffmpeg 命令；所有 ffmpeg 操作必须通过上述子命令或公共工具完成。机器资源限制、编码线程数、分辨率上限、低载参数等属于部署环境差异，读取 Content Producer workspace 的 `MEMORY.md` 或 Brief 中的环境约束，不写入本 Pipeline。

## 闸门

- **GATE A（文本闸门）**：口播/脚本、叙事节拍、意象桥、产品段与素材支撑计划齐备后，向 Brief owner 呈交摘要。若 main 已在 Brief 中代理批准 GATE A，记录批准范围后继续；否则停下等待批准。
- **GATE B（素材闸门）**：素材清单、授权记录、候选区 contact sheet、风险检查与交付承诺齐备后，向 Brief owner 呈交。批准人是用户或 main，按 Brief `gates` 字段执行。
- Brief 变更时升版本；已开工中间产物按新版取舍，弃用部分记入 `final-deliver.md`。

## 交付物

```text
<project-dir>/
  brief.md
  voiceover.md                    # main 交付口播时
  script/                         # 脚本、分镜、决策与自评
  materials/                      # 原始素材与授权记录
  render/                         # AIGC / 处理后素材
  audio/                          # 口播、字幕、混音
  video.mp4
  cover.jpg
  publish-desc.md                 # 平台包装文案或视频简介/署名/AI 标注/允许出现的链接
  final-deliver.md                # 素材来源、授权、段时长、自检、遗留问题
```

`publish-desc.md` 是发布说明，不是成片内容。Content Producer 不发布、不私信用户；预览由 Brief owner 或用户侧渠道发送。

## 验收检查

1. 正片零 URL、零域名、零联系方式。
2. 品牌名、产品名、能力表述与 Brief 一致；无收益承诺。
3. 叙事单线闭环，节拍 ≤ 6，转折因果可追。
4. 产品段占比、反转点位置与选定变体一致。
5. 每段素材来源与授权可追溯；AIGC 标注完整。
6. 口播、字幕、画面、音效与 Brief / `voiceover.md` 一致。
7. `video-review` verdict 为 pass；未通过不得交付。
8. 交付说明包含弃用中间产物、fallback 决策和遗留问题。
