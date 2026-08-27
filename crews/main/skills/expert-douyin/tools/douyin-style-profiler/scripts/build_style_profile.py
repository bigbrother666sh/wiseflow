#!/usr/bin/env python3
import argparse, json, math, re, shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


SENTENCE_SPLIT = re.compile(r"[。！？!?]+")
TOKEN_RE = re.compile(r"[一-鿿A-Za-z0-9_]+")
ENGLISH_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
SECOND_PERSON_RE = re.compile(r"你们?|you", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"我们?|I|we", re.IGNORECASE)
QUESTION_RE = re.compile(r"[？?]")
EXCLAMATION_RE = re.compile(r"[！!]")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
SOURCE_BLOCK_RE = re.compile(r"<!-- source-transcript\n(?P<path>.*?)\n-->", re.DOTALL)
REPORT_BLOCK_RE = re.compile(r"<!-- dna-reports\n(?P<paths>.*?)\n-->", re.DOTALL)

STATISTICS_METRICS = [
    "avg_sentence_tokens",
    "question_density_per_100_sentences",
    "second_person_density_per_100_sentences",
    "first_person_density_per_100_sentences",
    "exclamation_density_per_1000_characters",
    "speech_chars_per_minute",
]

STOP_TERMS = {
    "一个", "我们", "你们", "这里", "不会", "这个", "那个", "什么", "可以", "因为",
    "但是", "所以", "还是", "以及", "如果", "他们", "自己", "的时候", "to", "the",
    "a", "an", "is", "are", "and", "or", "of", "in", "for", "on", "with", "you", "we",
}

DIMENSION_GROUPS = {
    "选题与包装": [
        ("topic-angle", "选题角度"),
        ("title-style", "标题与文案"),
        ("cover-frame", "封面与首帧"),
    ],
    "钩子与表达": [
        ("hook", "3秒钩子"),
        ("word-habit", "用词习惯"),
        ("speech-rhythm", "口播节奏"),
        ("tone", "语气与人设感"),
    ],
    "视觉与制作": [
        ("shot-language", "镜头语言"),
        ("visual-style", "画面风格"),
        ("sound-design", "声音与BGM"),
    ],
    "结构与节奏": [
        ("video-structure", "视频结构模式"),
        ("narrative-rhythm", "叙事节奏"),
        ("conflict-tension", "冲突与张力"),
        ("professionalism", "专业度体现"),
    ],
    "互动与标记": [
        ("interaction-design", "互动设计"),
        ("signature", "签名式标记"),
        ("series-design", "系列化与合集"),
    ],
}
DIMENSIONS = []
number = 1
for group, dimensions in DIMENSION_GROUPS.items():
    for dimension_id, name in dimensions:
        DIMENSIONS.append(
            {"id": dimension_id, "number": number, "name": name, "group": group}
        )
        number += 1


def split_sentences(text: str) -> list[str]:
    return [item.strip() for item in SENTENCE_SPLIT.split(text) if item.strip()]

def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)

def rounded(value: float) -> float:
    return round(value, 4)

def safe_ratio(numerator: int, denominator: int, multiplier: float = 1) -> float:
    return rounded((numerator / denominator) * multiplier) if denominator else 0.0

def average(values: list[float]) -> float:
    return rounded(sum(values) / len(values)) if values else 0.0


def extract_terms(text: str) -> Counter:
    terms: Counter = Counter()
    for token in tokenize(text):
        if re.fullmatch(r"[A-Za-z0-9_]+", token):
            term = token.lower()
            if term not in STOP_TERMS and len(term) > 1:
                terms[term] += 1
            continue
        cleaned = "".join(ENGLISH_WORD_RE.sub("", token).split())
        if len(cleaned) == 1:
            continue
        for start in range(len(cleaned) - 1):
            term = cleaned[start : start + 2]
            if term not in STOP_TERMS:
                terms[term] += 1
    return terms


def title_candidates(path: Path, text: str) -> list[str]:
    candidates = [path.stem]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 2:
            candidates.append(stripped[2:].strip())
            break
    return candidates


def document_metrics(path: Path, text: str, duration: float = 0.0) -> dict:
    sentences = split_sentences(text)
    sentence_lengths = [len(tokenize(sentence)) for sentence in sentences]
    sentence_count = len(sentences)
    character_count = len(text)
    speech_chars_per_minute = (
        rounded(character_count / duration * 60) if duration > 0 else 0.0
    )

    return {
        "source_transcript": str(path.resolve()),
        "title_candidates": title_candidates(path, text),
        "characters": character_count,
        "sentences": sentence_count,
        "duration": duration,
        "avg_sentence_tokens": average([float(value) for value in sentence_lengths]),
        "question_density_per_100_sentences": safe_ratio(
            len(QUESTION_RE.findall(text)), sentence_count, 100
        ),
        "second_person_density_per_100_sentences": safe_ratio(
            len(SECOND_PERSON_RE.findall(text)), sentence_count, 100
        ),
        "first_person_density_per_100_sentences": safe_ratio(
            len(FIRST_PERSON_RE.findall(text)), sentence_count, 100
        ),
        "exclamation_density_per_1000_characters": safe_ratio(
            len(EXCLAMATION_RE.findall(text)), character_count, 1000
        ),
        "speech_chars_per_minute": speech_chars_per_minute,
        "terms": dict(extract_terms(text)),
    }


def collect_input_paths(inputs: list[str], suffixes: set[str]) -> list[Path]:
    paths: list[Path] = []
    for input_value in inputs:
        input_path = Path(input_value).expanduser()
        if not input_path.exists():
            raise SystemExit(f"Input does not exist: {input_path}")
        if input_path.is_dir():
            paths.extend(
                path
                for path in input_path.rglob("*")
                if path.is_file() and path.suffix.lower() in suffixes
            )
        elif input_path.is_file() and input_path.suffix.lower() in suffixes:
            paths.append(input_path)
        else:
            raise SystemExit(f"Input must be a {', '.join(sorted(suffixes))} file or directory: {input_path}")
    unique = {path.resolve(): path for path in paths}
    return sorted(unique.values(), key=lambda path: str(path))


def validate_cover_image(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_file():
        raise SystemExit(f"Cover image does not exist: {path}")
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise SystemExit("--cover-image must be a local .jpg/.jpeg/.png/.webp/.gif file")
    return path


def persist_cover_image(cover_image: Path, report_output_dir: Path, sample_id: str) -> Path:
    cover_dir = report_output_dir.parent / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)
    destination = cover_dir / f"{sample_id}{cover_image.suffix.lower()}"
    shutil.copyfile(cover_image, destination)
    return destination


def yaml_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def metric_label(metric_name: str) -> str:
    labels = {
        "avg_sentence_tokens": "平均口播句长（token）",
        "question_density_per_100_sentences": "问句密度 / 百句",
        "second_person_density_per_100_sentences": "第二人称密度 / 百句",
        "first_person_density_per_100_sentences": "第一人称密度 / 百句",
        "exclamation_density_per_1000_characters": "感叹号密度 / 千字",
        "speech_chars_per_minute": "口播密度（字/分钟）",
    }
    return labels.get(metric_name, metric_name)


def weighted_median(pairs: list[tuple[float, float]]) -> float:
    ordered = sorted(pairs, key=lambda pair: pair[0])
    total_weight = sum(weight for _, weight in ordered)
    if total_weight == 0:
        return 0.0
    midpoint = total_weight / 2
    cumulative = 0.0
    for value, weight in ordered:
        previous = cumulative
        cumulative += weight
        if cumulative >= midpoint and previous < midpoint:
            return rounded(value)
    return rounded(ordered[-1][0])


def weighted_mad(pairs: list[tuple[float, float]], center: float) -> float:
    deviations = [(abs(value - center), weight) for value, weight in pairs]
    return weighted_median(deviations)


def build_statistics(reports: list[dict]) -> dict:
    total_weight = rounded(sum(report["weight"] for report in reports))
    numeric_metrics = {}
    for metric_name in STATISTICS_METRICS:
        pairs = [
            (float(report["document"][metric_name]), float(report["weight"]))
            for report in reports
        ]
        center = weighted_median(pairs)
        numeric_metrics[metric_name] = {
            "weighted_median": center,
            "weighted_mad": weighted_mad(pairs, center),
            "min": rounded(min(value for value, _ in pairs)) if pairs else 0.0,
            "max": rounded(max(value for value, _ in pairs)) if pairs else 0.0,
        }

    term_weights: dict[str, float] = defaultdict(float)
    term_counts: dict[str, list[int]] = defaultdict(list)
    for report in reports:
        for term, count in report["document"]["terms"].items():
            term_weights[term] += report["weight"]
            term_counts[term].append(count)
    stable_terms = []
    for term, coverage_weight in term_weights.items():
        stable_terms.append(
            {
                "term": term,
                "weighted_coverage": rounded(coverage_weight / total_weight),
                "report_count": len(term_counts[term]),
                "median_count_per_report": rounded(median(term_counts[term])),
            }
        )
    stable_terms.sort(
        key=lambda item: (item["weighted_coverage"], item["report_count"], item["term"]),
        reverse=True,
    )

    weights = [report["weight"] for report in reports]
    return {
        "report_count": len(reports),
        "total_weight": total_weight,
        "weighting": "user-specified" if any(abs(weight - 1) > 1e-9 for weight in weights) else "uniform",
        "numeric_metrics": numeric_metrics,
        "stable_terms": stable_terms[:30],
        "weighted_coverage": sorted(
            (
                {
                    "report_id": report["report_id"],
                    "weight": report["weight"],
                    "focus": report["focus"],
                }
                for report in reports
            ),
            key=lambda item: item["weight"],
            reverse=True,
        ),
    }


def statistics_markdown(statistics: dict) -> str:
    lines = [
        "| 指标 | 加权中位数 | 加权 MAD | 最小值 | 最大值 |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric_name, values in statistics["numeric_metrics"].items():
        lines.append(
            f"| {metric_label(metric_name)} | {values['weighted_median']} | {values['weighted_mad']} | {values['min']} | {values['max']} |"
        )
    lines.extend(
        [
            "",
            f"权重模式：`{statistics['weighting']}`；总权重：`{statistics['total_weight']}`。",
            "口播密度（字/分钟）仅在 report 提供 `duration` 时有意义；未提供时该行只是 0 值占位。",
            "统计只用于辅助聚合，不生成评分；定性判断必须回到各篇 DNA report。",
        ]
    )
    return "\n".join(lines)


def parse_frontmatter(markdown: str) -> dict[str, str]:
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", markdown, re.DOTALL)
    if not match:
        raise SystemExit("DNA markdown is missing frontmatter")
    values = {}
    for line in match.group("body").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def parse_quoted(value: str) -> str:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip('"')


def parse_json_list(value: str) -> list:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def parse_duration(value: str) -> float:
    try:
        duration = float(value)
    except ValueError:
        return 0.0
    return duration if math.isfinite(duration) and duration > 0 else 0.0


def hidden_path(block_match, path_key: str = "paths") -> list[Path]:
    if not block_match:
        return []
    return [Path(line.strip()) for line in block_match.group(path_key).splitlines() if line.strip()]


def load_reports(paths: list[Path]) -> list[dict]:
    reports = []
    for path in paths:
        markdown = path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(markdown)
        source_match = SOURCE_BLOCK_RE.search(markdown)
        source_paths = hidden_path(source_match, "path")
        source_path = source_paths[0] if source_paths else Path(parse_quoted(metadata.get("source-transcript", "")))
        if not source_path.is_file():
            raise SystemExit(f"DNA report source transcript does not exist: {source_path}")
        duration = parse_duration(metadata.get("duration", "0"))
        document = document_metrics(
            source_path,
            source_path.read_text(encoding="utf-8", errors="ignore"),
            duration,
        )
        reports.append(
            {
                "report_path": str(path.resolve()),
                "dna_id": parse_quoted(metadata.get("dna-id", "")),
                "report_id": parse_quoted(metadata.get("report-id", path.name.removesuffix(".report.md"))),
                "title": parse_quoted(metadata.get("title", document["title_candidates"][-1])),
                "weight": float(metadata.get("weight", "1")),
                "focus": parse_json_list(metadata.get("focus", "[]")),
                "document": document,
            }
        )
    return reports


def report_dimension_markdown(dimension: dict) -> str:
    heading = f"### {dimension['number']}. {dimension['name']}"
    if dimension["id"] == "cover-frame":
        return (
            f"{heading}\n\n"
            "**视觉模型分析：**待 Agent 基于封面 / 首帧图补齐。\n\n"
            "- 画面主体与场景：待 Agent 补齐。\n"
            "- 构图与画幅：待 Agent 补齐。\n"
            "- 色彩体系：待 Agent 补齐。\n"
            "- 光线与质感：待 Agent 补齐。\n"
            "- 风格与媒介：待 Agent 补齐。\n"
            "- 文字视觉与图文关系（封面字 / 贴纸 / 标题框）：待 Agent 补齐。\n"
            "- 品牌识别元素：待 Agent 补齐。\n"
            "- 避免项：待 Agent 补齐。\n\n"
            "**AIGC 复现提示词要素：**待 Agent 补齐；要求能据此生成风格高度一致的封面图。\n\n"
            "**可复用创作信号：**待 Agent 补齐。"
        )
    if dimension["id"] == "hook":
        return (
            f"{heading}\n\n"
            "**钩子原文（前 3 秒口播 / 首帧字幕）：**待 Agent 逐字摘录。\n\n"
            "**单条结论：**待 Agent 补齐（钩子类型、是否对应定位、正文是否兑现）。\n\n"
            "**原文证据：**待 Agent 补齐。\n\n"
            "**可复用创作信号：**待 Agent 补齐。"
        )
    return (
        f"{heading}\n\n"
        "**单条结论：**待 Agent 补齐。\n\n"
        "**原文证据：**待 Agent 补齐（口播逐字引用或画面描述，注明时间区间）。\n\n"
        "**可复用创作信号：**待 Agent 补齐。"
    )


def report_markdown(
    dna_id: str,
    report_id: str,
    weight: float,
    focus: list[str],
    document: dict,
    cover_image: str,
    source_url: str,
) -> str:
    dimensions = []
    for dimension in DIMENSIONS:
        dimensions.append(report_dimension_markdown(dimension))
    duration_line = f"duration: {document['duration']}"
    return "\n\n".join(
        [
            "---\n"
            f"dna-id: {yaml_value(dna_id)}\n"
            f"report-id: {yaml_value(report_id)}\n"
            "type: dna-report\n"
            f"title: {yaml_value(document['title_candidates'][-1])}\n"
            f"source-transcript: {yaml_value(document['source_transcript'])}\n"
            f"source-url: {yaml_value(source_url)}\n"
            f"cover-image: {yaml_value(cover_image)}\n"
            f"{duration_line}\n"
            f"weight: {weight}\n"
            f"focus: {yaml_value(focus)}\n"
            "sample_count: 1\n"
            f"generated_at: {yaml_value(generated_at())}\n"
            "---",
            f"# {document['title_candidates'][-1]} 单条 DNA Report",
            "本文件只描述这一条视频。它不是聚合后的 DNA 文档，也不直接作为生产模板。",
            "## 单条统计",
            f"- 转录字符：{document['characters']}\n- 口播句子：{document['sentences']}\n- 视频时长：{document['duration'] or '未提供'}\n- 标题候选：{' / '.join(document['title_candidates'])}\n- 来源链接：{source_url or '未提供'}\n- 封面 / 首帧图：{cover_image or '未提供'}",
            f"## {len(DIMENSIONS)} 维单条分析",
            "\n\n".join(dimensions),
            "## 单条边界",
            "- 这里记录本条视频的可复用信号，不判断跨条稳定性。\n- 聚合时由 Agent 根据 DNA report、权重和 focus 判断共性、偏好和例外。",
            f"<!-- source-transcript\n{document['source_transcript']}\n-->",
            *( [f"<!-- source-cover\n{cover_image}\n-->"] if cover_image else [] ),
        ]
    ) + "\n"


def user_input_markdown(user_inputs: list[str], existing_body: str | None = None) -> str:
    if not user_inputs:
        return existing_body or "暂无待转译输入。"
    entries = []
    for index, user_input in enumerate(user_inputs, start=1):
        entries.append(
            f"### 输入 {index}\n"
            f"- raw_input: {yaml_value(user_input)}\n"
            f"- affected_dimensions: 待 Agent 映射到 {len(DIMENSIONS)} 个维度 ID\n"
            "- dna_document_change: 待 Agent 转译为聚合结论 / 报告依据 / 创作规则\n"
            "- template_change: 待 Agent 转译为具体执行规则\n"
            "- status: pending"
        )
    if existing_body and existing_body != "暂无待转译输入。":
        return existing_body + "\n\n" + "\n\n".join(entries)
    return "\n\n".join(entries)


def dna_document_markdown(
    dna_id: str,
    reports: list[dict],
    statistics: dict,
    user_inputs: list[str] | None = None,
    previous_dna: str | None = None,
) -> str:
    old_sections = extract_markdown_sections(previous_dna, "### ")
    dimensions = []
    for dimension in DIMENSIONS:
        heading = f"### {dimension['number']}. {dimension['name']}"
        body = old_sections.get(heading)
        if body:
            dimensions.append(f"{heading}\n\n{body}")
        else:
            if dimension["id"] == "cover-frame":
                dimensions.append(
                    f"{heading}\n\n**聚合结论：**待 Agent 补齐。\n\n"
                    "**报告依据：**待 Agent 列出使用的封面 / 首帧图和 DNA report。\n\n"
                    "**视觉生成规则：**待 Agent 转成可执行的 AIGC 提示词要素。\n\n"
                    "**例外与约束：**待 Agent 补齐。"
                )
            else:
                dimensions.append(
                    f"{heading}\n\n**聚合结论：**待 Agent 补齐。\n\n"
                    "**报告依据：**待 Agent 列出使用的 DNA report、权重和 focus。\n\n"
                    "**创作规则：**待 Agent 补齐。"
                )
    report_paths = "\n".join(report["report_path"] for report in reports)
    existing_user_inputs = (
        extract_named_section(previous_dna, "## 用户输入转译区") if previous_dna else None
    )
    return "\n\n".join(
        [
            "---\n"
            f"dna-id: {yaml_value(dna_id)}\n"
            "type: dna-document\n"
            f"report_count: {statistics['report_count']}\n"
            f"total_weight: {statistics['total_weight']}\n"
            f"weighting: {statistics['weighting']}\n"
            f"generated_at: {yaml_value(generated_at())}\n"
            "---",
            f"# {dna_id} DNA 文档",
            "本文件聚合历史 DNA report。它是账号当前采用的短视频内容与风格规则，也必须能推导出生产模板。",
            "## 报告与权重",
            "\n".join(
                f"- `{report['report_path']}`：weight `{report['weight']}`，focus `{', '.join(report['focus']) or 'all'}`"
                for report in reports
            ),
            statistics_markdown(statistics),
            f"## {len(DIMENSIONS)} 维聚合",
            "\n\n".join(dimensions),
            "## 用户输入转译区",
            user_input_markdown(user_inputs or [], existing_user_inputs),
            "## 推导规则",
            "- 聚合结论必须能追溯到 DNA report。\n- 用户输入必须先映射到具体维度，再修改聚合结论和创作规则；不得把原话直接当成 DNA 规则。\n- 模板必须由本文件推导，不能引入本文件未确认的规则。",
            f"<!-- dna-reports\n{report_paths}\n-->",
        ]
    ) + "\n"


def extract_markdown_sections(markdown: str | None, heading_prefix: str) -> dict[str, str]:
    if not markdown:
        return {}
    sections = {}
    current_heading = None
    current_level = 0
    current_lines = []
    for line in markdown.splitlines():
        match = re.match(r"^(?P<level>#{1,6})\s+", line)
        if match:
            level = len(match.group("level"))
            if current_heading is not None and level <= current_level:
                sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = None
                current_level = 0
                current_lines = []
            if line.startswith(heading_prefix):
                current_heading = line
                current_level = level
                current_lines = []
            elif current_heading is not None:
                current_lines.append(line)
            continue
        if current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def extract_named_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    found = False
    body = []
    for line in lines:
        if found:
            if line.startswith("## "):
                break
            body.append(line)
        elif line.strip() == heading:
            found = True
    return "\n".join(body).strip()


TEMPLATE_STAGES = ("起", "承", "转", "合", "CTA")

TEMPLATE_STAGE_FIELDS = {
    "起": (
        "本段任务",
        "钩子类型",
        "开场口播",
        "画面呈现",
        "句式节奏",
        "必须做",
        "避免",
    ),
    "承": (
        "本段任务",
        "推进逻辑",
        "信息密度",
        "镜头与画面",
        "口播表达",
        "证据与素材",
        "必须做",
        "避免",
    ),
    "转": (
        "本段任务",
        "转折触发",
        "冲突与反差",
        "情绪表达",
        "句式节奏",
        "必须做",
        "避免",
    ),
    "合": (
        "本段任务",
        "收束方式",
        "情绪落点",
        "签名式标记",
        "必须做",
        "避免",
    ),
    "CTA": (
        "行动目标",
        "表达方式",
        "时机与位置",
        "受众关联",
        "必须做",
        "避免",
    ),
}


def parse_template_fields(body: str) -> dict[str, str]:
    fields = {}
    for line in body.splitlines():
        match = re.match(r"^（(?P<label>[^：]+)：(?P<value>.+)）$", line.strip())
        if match:
            fields[match.group("label")] = match.group("value")
    return fields


def template_stage_from_heading(heading: str) -> str | None:
    for stage in TEMPLATE_STAGES:
        if heading.startswith(f"[{stage}部分]"):
            return stage
    return None


def template_segment(stage: str, values: dict[str, str] | None = None) -> str:
    values = values or {}
    lines = [f"[{stage}部分]"]
    for field in TEMPLATE_STAGE_FIELDS[stage]:
        value = values.get(field, "待 Agent 补齐。")
        lines.append(f"（{field}：{value}）")
    return "\n".join(lines)


def extract_topic_title_body(previous_template: str | None) -> str:
    if not previous_template:
        return ""
    for heading in ("## 生产模板", "## 选题与标题"):
        body = extract_named_section(previous_template, heading)
        if not body:
            continue
        topic_title_lines = []
        for line in body.splitlines():
            # 只在真正的模板分段（[起部分] 等）处截断；[标题] 属于选题与标题区，必须保留。
            if re.match(r"^\[[^\]]+部分\]$", line.strip()):
                break
            topic_title_lines.append(line)
        rendered = "\n".join(topic_title_lines).strip()
        if rendered:
            return rendered
    return ""


def stage_values_from_template(old_sections: dict[str, str]) -> dict[str, dict[str, str]]:
    values = {stage: {} for stage in TEMPLATE_STAGES}
    for heading in sorted(old_sections, key=template_order):
        stage = template_stage_from_heading(heading)
        if not stage:
            continue
        for field, value in parse_template_fields(old_sections[heading]).items():
            values[stage][field] = value
    return values


def template_markdown(
    dna_id: str,
    source_dna: str,
    previous_template: str | None = None,
) -> str:
    old_sections = extract_template_sections(previous_template)
    stage_values = stage_values_from_template(old_sections)
    segments = [template_segment(stage, stage_values[stage]) for stage in TEMPLATE_STAGES]
    topic_title = extract_topic_title_body(previous_template) or (
        "（选题角度推荐：待 Agent 补齐。）\n"
        "（选题需考虑的受众关联角度：待 Agent 补齐。）\n"
        "\n"
        "[标题]（类型为主：待 Agent 补齐。）\n"
        "（参考：待 Agent 补齐。）\n"
        "（话题标签策略：待 Agent 补齐。）\n"
        "（封面 / 首帧风格：待 Agent 补齐。）\n"
        "（封面 AIGC 提示词要素：待 Agent 补齐。）"
    )
    if previous_template:
        for field in ("（封面 / 首帧风格：", "（封面 AIGC 提示词要素："):
            if field not in topic_title:
                topic_title += f"\n{field}待 Agent 补齐。）"
    section_defaults = [
        (
            "## 生产模板",
            topic_title + "\n\n" + "\n\n".join(segments),
        ),
        (
            "## 用户输入转译后的执行规则",
            "- （来自用户输入：待 Agent 补齐来源。）\n"
            f"- （影响维度：待 Agent 映射到 {len(DIMENSIONS)} 维 ID。）\n"
            "- （执行规则：待 Agent 写成生产时可直接执行的要求。）",
        ),
        (
            "## 使用检查",
            "- 选题与标题是否符合 DNA 文档的选题角度、受众关联和标题类型。\n"
            "- 起、承、转、合、CTA 五个部分是否完成各自任务。\n"
            "- 每个部分是否反映 DNA 文档中对应的钩子、口播、镜头、节奏、冲突、互动与签名标记。\n"
            "- 用户输入是否已转译为具体执行规则。",
        ),
    ]
    rendered_sections = []
    for heading, default_body in section_defaults:
        if heading == "## 生产模板":
            body = default_body
        else:
            previous_body = (
                extract_named_section(previous_template, heading) if previous_template else ""
            )
            body = previous_body or default_body
        rendered_sections.append(f"{heading}\n\n{body}")

    return "\n\n".join(
        [
            "---\n"
            f"dna-id: {yaml_value(dna_id)}\n"
            "type: dna-template\n"
            f"source_dna: {yaml_value(source_dna)}\n"
            f"generated_at: {yaml_value(generated_at())}\n"
            "---",
            f"# {dna_id} DNA Template",
            "本模板是视频生产时直接执行的 production template，必须由 DNA 文档推导；不得引入 DNA 文档未确认的规则。",
            *rendered_sections,
        ]
    ) + "\n"


def extract_template_sections(markdown: str | None) -> dict[str, str]:
    if not markdown:
        return {}
    sections = {}
    current = None
    lines = []
    in_segment = False
    for line in markdown.splitlines():
        if re.match(r"^\[[^\]]+部分\]$", line.strip()):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = line
            lines = []
            in_segment = True
        elif line.startswith("## ") and in_segment:
            if current:
                sections[current] = "\n".join(lines).strip()
            current = None
            lines = []
            in_segment = False
        elif current:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


def template_order(heading: str) -> tuple[int, str]:
    stage = template_stage_from_heading(heading)
    if stage:
        return (TEMPLATE_STAGES.index(stage) + 1, heading)
    return (10_000, heading)


def validate_id(value: str, label: str) -> None:
    if not ID_RE.fullmatch(value):
        raise SystemExit(f"{label} must be 2-64 chars: lowercase letters, digits, and hyphens")


def validate_focus(focus: list[str]) -> None:
    valid = {dimension["id"] for dimension in DIMENSIONS}
    unknown = sorted(set(focus) - valid)
    if unknown:
        raise SystemExit(f"Unknown focus: {', '.join(unknown)}")


def validate_duration(value: str) -> float:
    try:
        duration = float(value)
    except ValueError:
        raise SystemExit("--duration must be a number of seconds")
    if duration < 0 or not math.isfinite(duration):
        raise SystemExit("--duration must be a non-negative finite number")
    return duration


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def inputs_from_args(args: argparse.Namespace) -> list[str]:
    if not args.input:
        raise SystemExit("Use --input FILE/DIR at least once")
    return args.input


def report_command(args: argparse.Namespace) -> None:
    validate_id(args.dna_id, "--dna-id")
    validate_id(args.sample_id, "--sample-id")
    validate_focus(args.focus)
    weight = float(args.weight)
    if weight <= 0 or not math.isfinite(weight):
        raise SystemExit("--weight must be a positive finite number")
    duration = validate_duration(args.duration) if args.duration else 0.0
    paths = collect_input_paths(inputs_from_args(args), {".md", ".txt"})
    if len(paths) != 1:
        raise SystemExit("report command accepts exactly one transcript; use build to aggregate reports")
    document = document_metrics(
        paths[0], paths[0].read_text(encoding="utf-8", errors="ignore"), duration
    )
    output_dir = Path(args.output_dir or f"dna/douyin/{args.dna_id}/reports")
    cover_image = ""
    if args.cover_image:
        source_cover = validate_cover_image(args.cover_image)
        cover_image = str(
            persist_cover_image(source_cover, output_dir, args.sample_id).resolve()
        )
    output = output_dir / f"{args.sample_id}.report.md"
    write_text(
        output,
        report_markdown(
            args.dna_id, args.sample_id, weight, args.focus, document, cover_image,
            args.source_url or "",
        ),
    )
    print(f"Wrote single-video DNA report: {output}")


def build_command(args: argparse.Namespace) -> None:
    validate_id(args.dna_id, "--dna-id")
    input_values = args.input or [f"dna/douyin/{args.dna_id}/reports"]
    paths = collect_input_paths(input_values, {".md"})
    report_paths = [path for path in paths if path.name.endswith(".report.md")]
    if not report_paths:
        raise SystemExit("build accepts DNA report .md files generated by the report command")
    reports = load_reports(report_paths)
    foreign_reports = [report["report_id"] for report in reports if report["dna_id"] != args.dna_id]
    if foreign_reports:
        raise SystemExit(
            f"Reports belong to another dna-id: {', '.join(foreign_reports)}"
        )
    statistics = build_statistics(reports)
    output_dir = Path(args.output_dir or f"dna/douyin/{args.dna_id}")
    dna_path = output_dir / f"{args.dna_id}.dna.md"
    template_path = output_dir / f"{args.dna_id}.template.md"
    write_text(
        dna_path,
        dna_document_markdown(args.dna_id, reports, statistics, args.user_input),
    )
    write_text(
        template_path,
        template_markdown(args.dna_id, dna_path.name, None),
    )
    print(f"Wrote DNA document and template: {output_dir}")


def update_command(args: argparse.Namespace) -> None:
    dna_path = Path(args.dna)
    template_path = Path(args.template)
    if not dna_path.is_file() or not template_path.is_file():
        raise SystemExit("Both --dna and --template must exist")
    previous_dna = dna_path.read_text(encoding="utf-8")
    previous_template = template_path.read_text(encoding="utf-8")
    metadata = parse_frontmatter(previous_dna)
    dna_id = parse_quoted(metadata.get("dna-id", dna_path.name.removesuffix(".dna.md")))
    validate_id(dna_id, "--dna-id")
    validate_focus(args.focus)

    input_values = args.input or []
    new_paths = collect_input_paths(input_values, {".md"}) if input_values else []
    new_reports = [path for path in new_paths if path.name.endswith(".report.md")]
    if input_values and not new_reports:
        raise SystemExit("update accepts DNA report .md files generated by the report command")
    historical = hidden_path(REPORT_BLOCK_RE.search(previous_dna))
    all_paths = {path.resolve(): path for path in [*historical, *new_reports]}
    reports = load_reports(sorted(all_paths.values(), key=lambda path: str(path)))
    foreign_reports = [report["report_id"] for report in reports if report["dna_id"] != dna_id]
    if foreign_reports:
        raise SystemExit(
            f"Reports belong to another dna-id: {', '.join(foreign_reports)}"
        )
    statistics = build_statistics(reports)
    user_inputs = list(args.user_input or [])
    write_text(
        dna_path,
        dna_document_markdown(
            dna_id,
            reports,
            statistics,
            user_inputs,
            previous_dna,
        ),
    )
    write_text(
        template_path,
        template_markdown(dna_id, dna_path.name, previous_template),
    )
    print(f"Updated DNA document and template: {dna_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build qualitative Douyin short-video DNA assets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Create one single-video DNA report")
    report.add_argument("--input", action="append", required=True)
    report.add_argument("--cover-image", help="Local cover / first-frame image used by visual-model analysis")
    report.add_argument("--source-url", help="Original video URL kept as report evidence")
    report.add_argument("--duration", help="Video duration in seconds, used for speech-density statistics")
    report.add_argument("--dna-id", required=True)
    report.add_argument("--sample-id", required=True)
    report.add_argument("--weight", default="1")
    report.add_argument("--focus", action="append", default=[])
    report.add_argument("--output-dir")
    report.set_defaults(handler=report_command)

    build = subparsers.add_parser("build", help="Aggregate DNA reports into DNA document and template")
    build.add_argument("--input", action="append")
    build.add_argument("--dna-id", required=True)
    build.add_argument("--user-input", action="append", default=[])
    build.add_argument("--output-dir")
    build.set_defaults(handler=build_command)

    update = subparsers.add_parser("update", help="Merge reports and translate user input")
    update.add_argument("--input", action="append")
    update.add_argument("--dna", required=True)
    update.add_argument("--template", required=True)
    update.add_argument("--focus", action="append", default=[])
    update.add_argument("--user-input", action="append", default=[])
    update.set_defaults(handler=update_command)
    return parser


def run(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    run()
