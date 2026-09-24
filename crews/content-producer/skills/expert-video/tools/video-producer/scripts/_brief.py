#!/usr/bin/env python3
"""_brief.py — Brief 字段解析共享助手（video-producer 流程链子命令用）。

从项目 brief.md 解析 workflow 字段与口播交付形态，供 script-write /
script-self-eval 做 workflow 感知，供各阶段脚本做 collage-broll 阶段裁剪守卫。

Brief 字段格式见 main 侧各平台 content-production 的 Brief 模板
（"- workflow：<值>"，中文冒号；口播文案行给 voiceover.md 绝对路径 / 录音路径 / 不适用）。
"""

from __future__ import annotations

import re
from pathlib import Path

TYPE_WORKFLOWS = {"reversal-ad", "narration-video", "collage-broll", "deck-talk"}

_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".amr"}


def read_brief(project: Path) -> str:
    brief = Path(project) / "brief.md"
    if not brief.is_file():
        return ""
    return brief.read_text(encoding="utf-8")


def parse_workflow(brief_text: str) -> str | None:
    """解析 Brief 的 workflow 字段。

    返回 'reversal-ad' / 'narration-video' / 'collage-broll' / 'deck-talk'；
    未指定、模板未填（枚举行原样 / 省略标注）或无 Brief → None。
    """
    for line in brief_text.splitlines():
        m = re.match(r"^-\s*workflow\s*[：:]\s*(.+)$", line.strip())
        if not m:
            continue
        val = m.group(1).strip().strip("`\"'")
        # 模板未填（多值枚举行原样）或明确省略 → 未指定
        if "省略" in val or "未指定" in val or val.startswith("reversal-ad /"):
            return None
        if val in TYPE_WORKFLOWS:
            return val
        # 单值带尾注（如 "reversal-ad（…）"）
        head = val.split("（")[0].split("(")[0].strip()
        return head if head in TYPE_WORKFLOWS else None
    return None


def detect_voiceover(project: Path, brief_text: str) -> tuple[str | None, Path | None]:
    """解析口播交付形态（口播 = 真人出镜 / 数字人 / 真人录音）。

    返回 ('voiceover', Path) / ('recording', Path) / (None, None)。
    都没有 → 旁白形态（TTS 配音解说，文稿由 CP 写）。
    """
    project = Path(project)
    cand = project / "voiceover.md"
    if cand.is_file():
        return "voiceover", cand
    for line in brief_text.splitlines():
        if "口播" not in line:
            continue
        for tok in re.findall(r"[\w./\-]+", line):
            p = Path(tok)
            if not p.suffix:
                continue
            if p.suffix == ".md" and "voiceover" in p.stem.lower() and p.is_file():
                return "voiceover", p
            if p.suffix.lower() in _AUDIO_EXTS and p.is_file():
                return "recording", p
    return None, None


def deck_fields(brief_text: str) -> dict[str, str]:
    """Read the explicit deck-talk branch and locked media references from a Brief."""
    keys = {'presenter_source', 'presenter', 'audio', 'visual_source', 'audio_origin'}
    result = {}
    for line in brief_text.splitlines():
        match = re.match(r'^-\s*([a-z_]+)\s*[：:]\s*(.*?)\s*$', line.strip())
        if match and match.group(1) in keys:
            result[match.group(1)] = match.group(2).strip('`')
    return result


def collage_guard(project: Path, stage: str) -> bool:
    """既有阶段裁剪入口；同时防止 deck-talk 误走通用 Stage 3–10。

    Brief 指定 collage-broll 且本阶段被其裁剪时，打印跳过指引并返回 True
    （caller 应据此 return，退出码 0）。其余情况返回 False，照常执行。
    """
    workflow = parse_workflow(read_brief(project))
    if workflow == "deck-talk":
        number = re.match(r"Stage (\d+)\b", stage)
        if number and 3 <= int(number.group(1)) <= 10:
            print(f"[skip] deck-talk 重定义/裁剪 {stage}，按 workflows/deck-talk.md 执行：")
            print("       逐页脚本与素材 → 同源音频/时间戳 → HTML 动效计划与承诺 → GATE B → deck-render。")
            print("       不生成通用镜头表，不使用 slideshow-risk / motion_ratio 的素材视频口径。")
            return True
        return False
    if workflow != "collage-broll":
        return False
    print(f"[skip] collage-broll 类型裁剪本阶段（{stage}）——阶段裁剪表见 workflows/collage-broll.md：")
    print("       Stage 3–9 由独立纸片素材与 HTML 预览（Phase 2）替代；成片走 `video-producer visual-render`（Phase 3）；")
    print("       默认无声、逐条独立成片不经拼接。按 workflow 文档执行，不要调用本命令。")
    return True
