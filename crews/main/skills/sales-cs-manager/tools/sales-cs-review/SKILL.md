---
name: sales-cs-review
description: >
  扫描 sales-cs workspace 的 feedback/ 目录聚合客户反馈，输出结构化摘要
  供复盘使用。只读不写。完整复盘流程见 sales-cs-manager 包内 Review workflow。
metadata:
  openclaw:
    emoji: 🛠️
---

# sales-cs-review 工具说明书

扫描 `~/.openclaw/workspace-sales-cs/feedback/*.md`，输出结构化摘要。建议怎么改（客服手册 / 话术 / IDENTITY）属于 Review workflow 的 agent 判断，不在本工具内。

## 命令

```bash
sales-cs-review
sales-cs-review --since 2026-06-01
```

## 输入输出

- 输入：sales-cs workspace `feedback/` 下的 `.md` 文件；无 `--since` 时扫描全部
- `--since YYYY-MM-DD`：按文件名中的日期过滤，只统计该日期之后的文件
- 输出（stdout，JSON）：
  - `total`：反馈条目数（按 `## Feedback:` 标题行计数）
  - `files`：扫描到的文件名列表
  - `keywords`：高频关键词及次数（投诉/退款/价格/试用/开票/人工/不满/bug/无法）
  - `entries`：每条反馈的文件、日期、标题
  - `feedback/` 目录不存在时输出 `total: 0` 及说明
- 退出码：`0` 成功（含无反馈）；`1` sales-cs workspace 不存在
- 环境变量 `SALES_CS_WORKSPACE` 可覆盖 workspace 路径

## 注意事项

- **只读**：不创建、不修改、不删除任何文件。`feedback/` 是客户反馈历史，只用于复盘。
- `keywords` 是字面计数，不是结论；关键词是否构成系统性问题由 agent 结合反馈原文判断。
- wrapper 薄转发到 `scripts/scan_feedback.py`，参数原样透传。
