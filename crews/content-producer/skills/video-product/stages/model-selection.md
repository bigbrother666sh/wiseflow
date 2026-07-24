# 模型选型与时长限制（stages/ 子文档）

> 主 SKILL.md 在此段只保留导航指针，脚本创作阶段（Step 2）和生产阶段（Step 4）按需 read 此文。

## 模型选型与时长限制（脚本创作时必须遵守）

视频素材优先使用 `gen.py` 脚本生成。

### 平台与模型

| 平台 | 环境变量 | 模型 |
|------|---------|------|
| 阿里云百炼（优先） | `MODELSTUDIO_API_KEY`（或 `DASHSCOPE_API_KEY`） | `happyhorse-1.1-i2v`、`happyhorse-1.1-t2v`、`happyhorse-1.1-r2v` |
| 火山引擎方舟 | `AWK_GEN_KEY` | `doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-260128`、`doubao-seedance-2-0-mini-260615` |

- 两个平台的上述模型**均支持声画同出**（t2v / i2v / r2v 三种模式）。
- **平台自动判断写在 `gen.py` 里**：有 `MODELSTUDIO_API_KEY` 走百炼，否则有 `AWK_GEN_KEY` 走火山，两者皆无则输出提示让 Agent 改用 `pexels-footage`/`pixabay-footage`（退出码 2）。

### 百炼模型选择规则

按模式选首选模型，`gen.py` 自动沿候选链 fallback（happyhorse-1.1 → 1.0 → wan2.7）。

| 模式 | 首选模型 | 适用场景 |
|------|---------|---------|
| **r2v**（A.1 人物叙事 + A.3 用户参考图） | `happyhorse-1.1-r2v` | A.1 人物故事全段（`--ref-image` 传 `character_reference.jpg`）；A.3 用户提供参考图片段（Step 3.4） |
| **t2v**（A.2 氛围叙事） | `happyhorse-1.1-t2v` | 手机底面、数据动画、产品特写等无重要人物的场景 |
| i2v | `happyhorse-1.1-i2v` | 如果需要指定首帧的话，使用`happyhorse-1.1-i2v`，传入图像会作为首帧图像。|

- 候选链（每模式一条）：`happyhorse-1.1-{mode}` → `happyhorse-1.0-{mode}` → `wan2.7-{mode}`。首选模型不可用或任务失败时 `gen.py` 自动沿链降级，无需人工干预。
- **`--model <id>` 可显式覆盖**（关闭候选链 fallback，只用该模型）；非必要不覆盖。

### WORKSPACE_ID 端点规则

配了 `WORKSPACE_ID` 时，happyhorse 走专属端点 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1`（华北2，更快）；没配则走默认 `https://dashscope.aliyuncs.com/api/v1`。

这个设置对于火山（doubao-seedance系列模型）无效。

### 火山候选链

- 候选链优先级：Fast → Normal → Mini；1080P 自动跳过 Fast（Fast 仅 720p）。
- ⚠️ **火山视频生成只认 `AWK_GEN_KEY`，不回退 `ARK_API_KEY`**：`ARK_API_KEY` 是火山主模型（doubao 对话）的 key，用户可能只想用火山主模型而不用火山生成视频；若回退会误触发火山视频生成。想用火山生成视频必须单独配 `AWK_GEN_KEY`。

### 模式与时长上限

| 模式 | 触发条件 | 百炼happyhorse-1.1上限 | 火山doubao-seedance上限 |
|------|---------|---------|---------|
| t2v（文生视频） | 无 `--image`/`--ref-image`/`--ref-video` | 3–15s | 2–15s |
| i2v（图生视频） | `--image`（首帧） | 3–15s | 2–15s |
| r2v（参考生视频） | `--ref-image`（用户提供参考图） | 3–15s | 2–15s |

**脚本规划规则**：
- 每个片段时长 **不得超过 15 秒**
- 超过上限的内容**必须在脚本中拆成多个片段**

---

