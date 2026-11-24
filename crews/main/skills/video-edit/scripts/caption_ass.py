#!/usr/bin/env python3
"""将 awk-tts 全部字级时间码与口播稿校验对齐，生成不重叠的 ASS。"""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata

from burn_subtitles import probe_video


def spoken(char: str) -> bool:
    return not char.isspace() and not unicodedata.category(char).startswith("P")


def align(text: str, data: dict) -> list[tuple[float, float, int]]:
    """保留词块原始时间；不为词块内部凭空插值。标点可以由原稿补齐。"""
    if not isinstance(data, dict) or not isinstance(data.get("sentences"), list):
        raise ValueError("TTS JSON 必须包含 sentences 数组")
    letters, times = [], []
    previous = 0.0
    for sentence in data.get("sentences", []):
        if not isinstance(sentence, dict) or not isinstance(sentence.get("words"), list):
            raise ValueError("每个 TTS sentence 必须包含 words 数组")
        for word in sentence.get("words", []):
            if not isinstance(word, dict) or not isinstance(word.get("word"), str):
                raise ValueError("每个 TTS word 必须包含 word 字符串")
            chars = [char for char in word["word"] if spoken(char)]
            if not chars:
                continue
            start, end = float(word["startTime"]), float(word["endTime"])
            if not all(map(math.isfinite, (start, end))) or not 0 <= start < end:
                raise ValueError("TTS 包含无效时间码")
            if start < previous - 0.01:
                raise ValueError("TTS 时间码倒序或重叠；请核对全部 sentences 是否使用同一音轨时间轴")
            token = len(letters)
            letters.extend(chars)
            times.extend([(start, end, token)] * len(chars))
            previous = end
    expected = "".join(char for char in text if spoken(char))
    if not expected or "".join(letters) != expected:
        raise ValueError("口播稿与 TTS 字词不一致（仅忽略空白和标点）；不得按字符数强行对齐")
    return times


def split_clauses(text: str) -> list[str]:
    clauses, start, index = [], 0, 0
    while index < len(text):
        char = text[index]
        numeric = (char in ",." and index > 0 and index + 1 < len(text)
                   and text[index - 1].isdigit() and text[index + 1].isdigit())
        if char in "，。？！；,.!?;\n" and not numeric:
            end = index + 1
            while end < len(text) and text[end] in "，。？！；,.!?;”’」』）》】":
                end += 1
            clauses.append(text[start:end])
            start = end
            index = end
        else:
            index += 1
    if start < len(text):
        clauses.append(text[start:])
    # 连续标点/空行附到前一句，不生成没有时间码的事件。
    result = []
    prefix = ""
    for clause in clauses:
        if any(map(spoken, clause)):
            result.append(prefix + clause)
            prefix = ""
        elif result:
            result[-1] += clause
        else:
            prefix += clause
    if "".join(result) != text:
        raise ValueError("分句后未能完整还原口播稿")
    return result


TOKEN = re.compile(r"\d+(?:[.,]\d+)*(?:万亿|万元|亿元|公里|公斤|小时|分钟|毫秒|[万千亿百元岁年月日天秒米克人次台件个倍%％])?|[A-Za-z]+(?:[-'][A-Za-z]+)*|.")
CLOSING = set("，。？！；：、,.!?;:%％”’」』）》】")
OPENING = set("“‘「『（《【")


def wrap(text: str, columns: int, max_lines: int) -> list[str]:
    """有界平衡断行；保护数字单位、英文词和标点，不猜测语义。"""
    tokens = TOKEN.findall(" ".join(text.split()))
    lengths = [0]
    for token in tokens:
        lengths.append(lengths[-1] + len(token))
    for count in range(1, max_lines + 1):
        target = lengths[-1] / count

        @lru_cache(None)
        def solve(start: int, left: int):
            if left == 0:
                return (0, []) if start == len(tokens) else None
            best = None
            for end in range(start + 1, len(tokens) + 1):
                size = lengths[end] - lengths[start]
                if size > columns:
                    break
                if end < len(tokens) and (tokens[end][0] in CLOSING or tokens[end - 1][-1] in OPENING):
                    continue
                tail = solve(end, left - 1)
                if tail is None:
                    continue
                penalty = (size - target) ** 2
                if end < len(tokens) and tokens[end - 1][-1] not in CLOSING:
                    penalty += 2
                candidate = (penalty + tail[0], ["".join(tokens[start:end]).strip()] + tail[1])
                if best is None or candidate[0] < best[0]:
                    best = candidate
            return best

        result = solve(0, count)
        if result:
            return result[1]
    raise ValueError(f"小句无法排进 {max_lines} 行、每行 {columns} 字符；请在口播稿语义停顿处补标点或调整排版参数")


def cues_for(text: str, data: dict, duration: float, columns: int = 19,
             max_lines: int = 3, padding: float = 0.1, gap: float = 0.02,
             layout: list[list[str]] | None = None) -> list[dict]:
    times = align(text, data)
    if times[-1][1] > duration + 0.01:
        raise ValueError("旁白时间码超出视频时长；先修正声画时长，不能裁掉末句")
    cues, offset = [], 0
    clauses = split_clauses(text)
    if layout is not None and (not isinstance(layout, list) or len(layout) != len(clauses)):
        raise ValueError("layout 必须按分句顺序提供等长的行数组")
    for index, clause in enumerate(clauses):
        size = sum(map(spoken, clause))
        if offset and times[offset - 1][2] == times[offset][2]:
            raise ValueError("分句边界落在一个 TTS 词块内部；调整该处标点，不能伪造字级时间")
        lines = wrap(clause, columns, max_lines) if layout is None else layout[index]
        if layout is not None:
            compact = "".join(clause.split())
            if (not isinstance(lines, list) or not 1 <= len(lines) <= max_lines
                    or any(not isinstance(line, str) or not line.strip() or len(line) > columns
                           or "\n" in line or "\r" in line for line in lines)
                    or "".join("".join(line.split()) for line in lines) != compact):
                raise ValueError("layout 不能改字、漏字、超行或超宽")
            boundaries, offset_in_text = set(), 0
            for token in TOKEN.findall(compact):
                offset_in_text += len(token)
                boundaries.add(offset_in_text)
            offset_in_text = 0
            for line in lines:
                offset_in_text += len("".join(line.split()))
                if line.lstrip()[0] in CLOSING or line.rstrip()[-1] in OPENING or offset_in_text not in boundaries:
                    raise ValueError("layout 不能拆开数字单位/英文词，或使标点悬挂在行首行尾")
        cues.append({"text": clause, "lines": lines,
                     "speech_start": times[offset][0], "speech_end": times[offset + size - 1][1]})
        offset += size
    assert "".join(cue["text"] for cue in cues) == text
    for index, cue in enumerate(cues):
        start = max(0, cue["speech_start"] - padding)
        end = min(duration, cue["speech_end"] + padding)
        if index:
            start = max(start, (cues[index - 1]["speech_end"] + cue["speech_start"] + gap) / 2)
        if index + 1 < len(cues):
            end = min(end, (cue["speech_end"] + cues[index + 1]["speech_start"] - gap) / 2)
        # 先量化再校验；避免 ASS 百分秒舍入后重叠或产生零时长。
        cue["start_cs"] = math.ceil(start * 100 - 1e-8)
        cue["end_cs"] = math.floor(end * 100 + 1e-8)
        if cue["start_cs"] >= cue["end_cs"]:
            raise ValueError("字幕分句过短，量化后无法显示；合并相邻短句")
    return cues


def ass_time(value: int) -> str:
    hours, remainder = divmod(value, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centis:02}"


def build_ass(cues: list[dict], width: int, height: int, font_size: int,
              margin_v: int, margin_lr: int, font: str, box: bool) -> str:
    # BorderStyle=3 的底框用 OutlineColour；BackColour 是阴影色。
    outline_colour = "&H80000000" if box else "&H00000000"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H00FFFFFF,&H00FFFFFF,{outline_colour},&H80000000,-1,0,0,0,100,100,0,0,{3 if box else 1},2,0,2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for cue in cues:
        line = r"\N".join(cue["lines"])
        header += f"Dialogue: 0,{ass_time(cue['start_cs'])},{ass_time(cue['end_cs'])},Default,,0,0,0,,{line}\n"
    return header


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="字幕对应的最终画布视频；旁白必须从视频 0 秒起对齐")
    parser.add_argument("timestamps", help="awk-tts 产出的 .subtitle.json（秒）")
    parser.add_argument("--text-file", required=True, help="UTF-8 纯口播稿，不能含镜头说明")
    parser.add_argument("--output", required=True, help="输出 .ass，同时生成同名 .json 校验记录")
    parser.add_argument("--font", default="Noto Sans CJK SC")
    parser.add_argument("--font-size", type=int, help="画布像素，默认按宽度缩放 47/1080")
    parser.add_argument("--margin-v", type=int, help="距底边像素，默认画高 13%%；按主体和平台预览调整")
    parser.add_argument("--columns", type=int, default=19, help="每行最多字符数，默认 19")
    parser.add_argument("--max-lines", type=int, default=3)
    parser.add_argument("--padding", type=float, default=0.1, help="句首/尾扩展秒数，默认 0.1")
    parser.add_argument("--gap", type=float, default=0.02, help="相邻字幕最小间隔秒数，默认 0.02")
    parser.add_argument("--no-box", action="store_true", help="用黑描边代替半透明底框")
    parser.add_argument("--layout", help="可选 JSON 二维数组，按分句顺序指定语义断行；不改变文案或时间")
    parser.add_argument("--preview-dir", help="生成 ASS 后自动试渲最多 10 个句中点，含首末句和最短/最长句")
    args = parser.parse_args()
    try:
        if not shutil.which("ffprobe"):
            raise ValueError("ffprobe 未安装")
        output = Path(args.output).resolve()
        protected = {Path(path).resolve() for path in (args.input, args.timestamps, args.text_file)}
        if args.layout:
            protected.add(Path(args.layout).resolve())
        if output.suffix.lower() != ".ass" or protected & {output, output.with_suffix(".json")}:
            raise ValueError("输出必须是 .ass，且不能覆盖输入文件")
        video = probe_video(args.input)
        font_size = args.font_size if args.font_size is not None else max(1, round(video["width"] * 47 / 1080))
        margin_v = args.margin_v if args.margin_v is not None else round(video["height"] * 0.13)
        margin_lr = round(video["width"] / 18)
        columns = min(args.columns, (video["width"] - 2 * margin_lr) // font_size) if font_size > 0 else 0
        if min(font_size, columns, args.max_lines) <= 0 or not 0 <= margin_v < video["height"]:
            raise ValueError("字号、行宽、行数或边距无效")
        if not all(math.isfinite(value) and value >= 0 for value in (args.padding, args.gap)):
            raise ValueError("padding/gap 必须是有限非负数")
        if any(char in args.font for char in ",\n\r"):
            raise ValueError("字体名不能包含逗号或换行")
        text = Path(args.text_file).read_text(encoding="utf-8-sig").strip()
        if any(char in text for char in "{}\\"):
            raise ValueError("纯口播稿不能包含 ASS 控制字符 {、}、反斜杠")
        data = json.loads(Path(args.timestamps).read_text(encoding="utf-8-sig"))
        layout = json.loads(Path(args.layout).read_text(encoding="utf-8-sig")) if args.layout else None
        cues = cues_for(text, data, video["duration"], columns, args.max_lines, args.padding, args.gap, layout)
        content = build_ass(cues, video["width"], video["height"], font_size, margin_v, margin_lr, args.font, not args.no_box)
        if margin_v + max(len(cue["lines"]) for cue in cues) * font_size * 1.5 >= video["height"]:
            raise ValueError("字幕区域超出画布；请减少行数、字号或底边距")
        report = {"ok": True, "output": str(output), "video": video, "font_size": font_size,
                  "margin_v": margin_v, "columns": columns, "cues": cues,
                  "preview_times": sorted({round((cue["start_cs"] + cue["end_cs"]) / 200, 3)
                                            for cue in cues})}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        if args.preview_dir:
            if not shutil.which("ffmpeg"):
                raise ValueError("ffmpeg 未安装")
            count = len(cues)
            selected = {0, count - 1,
                        min(range(count), key=lambda index: cues[index]["end_cs"] - cues[index]["start_cs"]),
                        max(range(count), key=lambda index: len(cues[index]["text"]))}
            for index in (round(step * (count - 1) / 9) for step in range(10)):
                if len(selected) < 10:
                    selected.add(index)
            previews = []
            for index in sorted(selected):
                cue = cues[index]
                timestamp = (cue["start_cs"] + cue["end_cs"]) / 200
                path = Path(args.preview_dir).resolve() / f"caption_{index:04}_{timestamp:.3f}s.png"
                if path in protected:
                    raise ValueError("试渲图片不能覆盖输入文件")
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).with_name("burn_subtitles.py")), args.input,
                     str(output), "--preview-at", str(timestamp), "--output", str(path)],
                    capture_output=True, text=True,
                )
                if result.returncode:
                    raise ValueError("字幕试渲失败: " + result.stderr[-1000:])
                previews.append({"cue": index, "t": timestamp, "path": str(path)})
            report["previews"] = previews
        output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
