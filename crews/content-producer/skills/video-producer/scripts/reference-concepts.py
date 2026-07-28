#!/usr/bin/env python3
"""Stage 1 — reference-concepts：吃 main 喂入的 viral-chaser 报告出 2–3 差异化概念。

本技能不做视频下载/转写/抽帧——那是 viral-chaser 的活。只接报告原档当输入。

Usage:
  python3 scripts/reference-concepts.py <project_dir> --report-file path

入：project_dir（output_videos/<topic>/）+ viral-chaser 报告路径
出：project_dir/reference-driven/concepts.md（2–3 差异化概念 + 成本 + 备选路径）

无报告则跳过本阶段，agent 直入 Stage 2 story-develop（本脚本不报错退出）。
"""

import argparse
import sys
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 reference-concepts")
    parser.add_argument("project_dir", help="output_videos/<topic>/")
    parser.add_argument("--report-file", default=None, help="main 喂入的 viral-chaser 报告路径")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    out_dir = project / "reference-driven"
    out_dir.mkdir(parents=True, exist_ok=True)
    concepts_path = out_dir / "concepts.md"

    # checkpoint
    if concepts_path.is_file():
        print(f"[checkpoint] concepts.md 已存在，沿用：{concepts_path}")
        return

    if not args.report_file:
        print("[skip] 无 viral-chaser 报告输入，跳过 Stage 1，直入 Stage 2 story-develop")
        return

    report = Path(args.report_file)
    if not report.is_file():
        print(f"[warn] 报告文件不存在: {args.report_file}，跳过 Stage 1")
        return

    # 复制报告原档到工作区（不做任何下载/转写/抽帧，只存档供后续阶段参考）
    import shutil
    archived = out_dir / "viral-chaser-report.md"
    if not archived.is_file():
        shutil.copy2(report, archived)

    # 提示 agent 据报告出 2–3 差异化概念写入 concepts.md
    stub = f"""# 据参考片出的差异化概念（Stage 1）

## 参考片来源

{archived.name}（main agent 喂入的 viral-chaser 追爆报告原档，未做下载/转写/抽帧）。

## 概念候选（agent 据报告填）

> agent 读 archived 报告，出 2–3 个**差异化**概念（不抄原片，做差异化），每个概念含：
> - 名称与一句话定位
> - 与参考片的差异化点（节奏/钩子/结构/调性任一的差异化）
> - 预算估算（USD）
> - 备选路径（如该概念走不通的 fallback）

### 概念 1
（agent 填）

### 概念 2
（agent 填）

### 概念 3（可选）
（agent 填）

## 用户选定

> 呈交用户选定一个概念，写入 brief.md。未选定前不进 Stage 2。
"""
    concepts_path.write_text(stub, encoding="utf-8")
    print(f"[done] 报告已存档：{archived}")
    print(f"[stub] concepts.md 模板已落：{concepts_path}")
    print(f"[next] agent 据报告填概念 → 呈交用户选定 → 跑 story-develop（Stage 2）")


if __name__ == "__main__":
    main()
