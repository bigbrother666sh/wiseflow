---
name: camoufox-guard
description: 巡检 camoufox-bin 进程数，超阈值告警 + 清理孤儿进程，防 OOM 死机（it-engineer 心跳调用）
metadata:
  openclaw:
    emoji: 🦊
---

# camoufox-guard

巡检 camoufox-bin 进程数，防止泄漏堆积撑爆内存死机。

## 背景

camoufox-bin（反指纹 Firefox）进程泄漏堆积是本机反复 OOM 死机的元凶（07-17/07-27/07-29 三次）。
根因是 browser.ts close() 不退 daemon 致 camoufox-bin 孤儿化，7.1 未根治。本技能是兜底安全网：
心跳里检测堆积，超阈值告警，超硬限杀超龄孤儿，避免再 OOM。

## 用法

```bash
bash ./skills/camoufox-guard/scripts/guard.sh
```

由 it-engineer HEARTBEAT 定期调用。输出：
- 正常：`camoufox-guard: OK (N 个 camoufox-bin，阈值 6)`
- 告警：`⚠️ camoufox-bin = N` + 进程详情（pid/年龄/内存）
- 清理：`🔴 超硬限，清理 X 个超 30min 的孤儿` + kill 记录

## 阈值（环境变量可覆盖）

| 变量 | 默认 | 含义 |
|------|------|------|
| `CAMOUFOX_GUARD_THRESHOLD` | 6 | 告警阈值（并发上限） |
| `CAMOUFOX_GUARD_HARD_LIMIT` | 12 | 硬上限（超了杀最老孤儿） |
| `CAMOUFOX_GUARD_MAX_AGE_MIN` | 30 | 超此年龄(分钟)视为孤儿可杀 |

## 安全保证

只杀 **age > 30min** 的 camoufox-bin。活跃浏览器任务（发布/抓取，通常 < 30min）不受影响。
若清理后仍超硬限（孤儿非超龄），脚本建议重启 gateway。
