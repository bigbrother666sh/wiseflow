# 微信公众号 DNA 索引与组合规则

## 存储约定

- 本目录是 Main Workspace 的微信公众号 DNA 唯一运行时目录：`dna/wx_mp/`。
- 每个样本统计型 DNA 必须成对存在：
  - `<dna-id>.md`：内容生产时直接执行的 instruction。
  - `<dna-id>.evaluation.md`：可观测、可计算的评估方案。
  - `<dna-id>.metrics.json`：评估命令使用的统计目标与容差。
- 排版主题不属于 DNA，一律保存在 `wenyan-theme/` 并登记 `index.json`。

## 当前可用 DNA

| DNA | 类型 | 状态 | 适用场景 |
|-----|------|------|----------|
| `default-business.md` | 内容风格 | ✅ 可用 | 大多数商业 / 品牌 / 服务类公众号（默认） |
| `default-business.evaluation.md` | 评估方案 | ✅ 可用 | 评估稿件是否符合 Default Business DNA |

## 组合规则

1. 必选一个主 DNA；主 DNA 来自用户明示定位，或从历史文章统计建模。
2. 可叠加 0-2 个辅助 DNA；辅助 DNA 只改选题与局部语气，不覆盖主 DNA 核心承诺。
3. 冲突优先级：品牌红线 > 平台合规 > 主 DNA 语气 > 结构 > 选题 > 行动引导。
4. 未识别账号定位且用户未确认默认 DNA 时，先询问用户。
5. DNA 只影响内容、标题和表达策略，不影响排版主题、发布链路、打分标准与记录格式。

## 新增 DNA 流程

1. 按 `expert-wx-mp/workflows/style-dna.md` 收集全量可获取样本。
2. 运行 `wechat-style-profiler build` 生成三件套。
3. 结合 14 维证据矩阵补齐 `<dna-id>.md` 的直接执行指令。
4. 用户确认后在本表登记来源、样本数和置信度。
5. 后续生产前读取 instruction，生产后按 evaluation 命令计算自评。
