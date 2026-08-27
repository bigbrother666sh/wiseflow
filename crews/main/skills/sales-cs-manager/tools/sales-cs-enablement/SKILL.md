---
name: sales-cs-enablement
description: >
  sales-cs 启用的机械操作工具：awada channel 配置检查 + business_knowledge
  软链建立。完整启用流程见 sales-cs-manager 包内 Enablement workflow。
metadata:
  openclaw:
    emoji: 🤝
---

# sales-cs-enablement 工具说明书

启用 sales-cs 过程中的两个机械动作。编排（channel 选项讲解、IT engineer 派工、workspace 文档完善）属于 Enablement workflow，不在本工具内。

## 命令

```bash
sales-cs-enablement check-channel
sales-cs-enablement link        # 无参调用等价于 link
```

## check-channel

检查 `~/.openclaw/openclaw.json` 的 `channels.awada` 是否已配置（段存在且非空即视为已配置）。

- 输出：JSON 状态到 stdout（`configured` / `awada` / `path`）
- 退出码：`0` 已配置；`1` 未配置或解析失败；`2` 配置文件不存在
- 环境变量 `OPENCLAW_JSON` 可覆盖配置文件路径

## link

把 main agent workspace 的 `business_knowledge.md`（单文件正文）和 `business_knowledge/`（支撑材料文件夹）软链到 sales-cs workspace 同名位置。

- 源解析：优先 `~/.openclaw/workspace-main/`；`.md` 不存在时从仓库模板 `crews/main/business_knowledge.md` 复制一份到 main workspace；文件夹不存在时在仓库创建空目录
- 目标：`~/.openclaw/workspace-sales-cs/` 下的同名条目
- 目标已存在且是软链 -> 覆盖重建；已存在且是真实文件/目录 -> **报错拒绝覆盖**（退出码 1），防误删数据，需人工确认后处理
- 退出码：`0` 成功；`1` 目标为非软链或其他错误
- 环境变量 `MAIN_WORKSPACE` / `SALES_CS_WORKSPACE` / `REPO_MAIN` 可覆盖三个路径

## 注意事项

- 治理边界：业务知识由 main agent 维护，sales-cs 不自行维护（软链只读访问），避免绕过 main agent。
- wrapper 是子命令分发器：`check-channel` 转发诊断脚本 `check_awada_channel.py`，`link` 转发主入口 `symlink_business_knowledge.py`。agent 一律走 PATH 调用，不要拼脚本路径。
