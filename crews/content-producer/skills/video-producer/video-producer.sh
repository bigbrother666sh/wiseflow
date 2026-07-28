#!/usr/bin/env bash
# video-producer.sh — video-producer 顶层 wrapper（薄转发，子命令范式）
# 让 agent 用 `video-producer <子命令> [参数...]` 走 PATH，零路径拼接。
# 子命令即 scripts/ 下同名 .py，wrapper 转发到对应脚本，不改语义。
# 子命令清单见 SKILL.md；每阶段是 scripts/ 下一个独立脚本，
# agent 按 SKILL.md 工作流逐个调，产物文件存在性即 checkpoint（不引状态机）。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# Resolve symlink (wrapper is ln -sfn'd into ~/.openclaw/bin) so SCRIPT_DIR points at the real skill dir.
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"

SUBCMD="${1:?用法: video-producer <子命令> [参数...]}"
shift
case "$SUBCMD" in
  -h|--help|help)
    cat <<'HELP'
video-producer — 端到端视频制作（wrapper）

用法:
  video-producer <子命令> [参数...]      跑对应阶段的原子脚本
  video-producer help                    列可用子命令

子命令（按工作流阶段序）:
  intent-router        Stage 0  意图路由 → 三档脚本模板（故事讲述型/纯画面动效型/蒙太奇剪接型）
  reference-concepts   Stage 1  吃 viral-chaser 报告出 2–3 差异化概念（可选，无报告跳过）
  story-develop        Stage 2  idea → 故事（分场）
  script-write         Stage 3  故事 → 分场剧本（含 enhancement_cues + delivery_cues）
  script-self-eval     Stage 3  脚本自评 N 维打分
  storyboard-build     Stage 4  剧本 → 镜头表
  shot-decompose       Stage 5  每镜拆首尾帧 + 运动描述 + variation_type
  character-register   Stage 6  角色三视图 + static/dynamic features 拆分
  slot-plan            Stage 7  素材 slot 规划
  asset-resolve        Stage 8  按 slot 拉素材（Fast path 人核缩略图）
  slideshow-risk       Stage 9  六维幻灯风险打分（pre-compose 闸门）
  delivery-promise-lock Stage 9 交付承诺八类锁定
  render-shot          Stage 10 按 slot 渲染（AIGC i2v / 静图）
  mix-audio            Stage 11 旁白（awk-tts）+ BGM + 字幕
  assemble             Stage 12 按镜顺序拼接成片 + 转场
  motion-audit         Stage 13 motion_led 抽查（补公共 video-review）
  make-cover           Stage 14 封面（siliconflow-img-gen，必含标题文字）

闸门不是子命令——GATE A（Stage 6 后文本闸门）与 GATE B（Stage 9 后素材闸门）由 agent
按 SKILL.md 工作流执行：呈交摘要 → 结束本轮回复 → 等用户逐闸门批准。

产物文件存在性即 checkpoint：每个子命令先查产物文件是否存在，存在则 load 不重生成。
HELP
    ;;
  *)
    SCRIPT="$SCRIPT_DIR/scripts/${SUBCMD}.py"
    if [ ! -f "$SCRIPT" ]; then
      echo "未知子命令: $SUBCMD" >&2
      echo "用 video-producer help 查可用子命令" >&2
      exit 1
    fi
    exec python3 "$SCRIPT" "$@"
    ;;
esac
