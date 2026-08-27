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
# 小红书正文内联话题标签：#话题 （样本文件约定正文为纯文本，行首 # 只出现在标题行）
TAG_RE = re.compile(r"(?m)(?:^|(?<=\s))#[^\s#]\S*")
EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "☀-⛿"
    "✀-➿"
    "⬀-⯿"
    "️"
    "]"
)

STATISTICS_METRICS = [
    "title_chars",
    "avg_sentence_tokens",
    "line_count",
    "question_density_per_100_sentences",
    "second_person_density_per_100_sentences",
    "first_person_density_per_100_sentences",
    "exclamation_density_per_1000_characters",
    "emoji_count",
    "emoji_density_per_100_characters",
    "tag_count",
]

STOP_TERMS = {
    "一个", "我们", "你们", "这里", "不会", "这个", "那个", "什么", "可以", "因为",
    "但是", "所以", "还是", "以及", "如果", "他们", "自己", "的时候", "to", "the",
    "a", "an", "is", "are", "and", "or", "of", "in", "for", "on", "with", "you", "we",
}

DIMENSION_GROUPS = {
    "选题与包装": [
        ("topic-angle", "选题角度"),
        ("title-style", "标题风格"),
        ("cover-imageset", "封面与图组"),
        ("keyword-seo", "关键词与搜索流量"),
    ],
    "正文与表达": [
        ("opening-hook", "开头钩子"),
        ("body-structure", "正文结构"),
        ("language-tone", "口语语气与人设"),
        ("emoji-rhythm", "emoji与标点节奏"),
    ],
    "视觉与证据": [
        ("image-composition", "图片构图与信息"),
        ("visual-style", "视觉风格"),
        ("credibility-proof", "证据与人味"),
    ],
    "互动与转化": [
        ("interaction-design", "互动设计"),
        ("tag-strategy", "话题标签策略"),
        ("cta-conversion", "行动引导与转化"),
    ],
    "签名与系列": [
        ("signature-mark", "签名式标记"),
        ("series-design", "系列化设计"),
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


def split_title_body(text: str) -> tuple[str, str]:
    """样本文件约定：首个一级标题行为笔记标题，其余为正文（含内联 #话题）。"""
    title = ""
    body_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not title and stripped.startswith("# ") and len(stripped) > 2:
            title = stripped[2:].strip()
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return title, body


def title_candidates(path: Path, text: str) -> list[str]:
    candidates = [path.stem]
    title, _ = split_title_body(text)
    if title:
        candidates.append(title)
    return candidates


def document_metrics(path: Path, text: str) -> dict:
    title, body = split_title_body(text)
    sentences = split_sentences(text)
    sentence_lengths = [len(tokenize(sentence)) for sentence in sentences]
    sentence_count = len(sentences)
    character_count = len(text)
    body_lines = [line for line in body.splitlines() if line.strip()]
    emoji_count = len(EMOJI_RE.findall(body))
    tag_count = len(TAG_RE.findall(body))

    return {
        "source_transcript": str(path.resolve()),
        "title_candidates": title_candidates(path, text),
        "characters": character_count,
        "sentences": sentence_count,
        "title_chars": len(title),
        "line_count": len(body_lines),
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
        "emoji_count": emoji_count,
        "emoji_density_per_100_characters": safe_ratio(
            emoji_count, len(body), 100
        ),
        "tag_count": tag_count,
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
        "title_chars": "标题字数",
        "avg_sentence_tokens": "平均句长（token）",
        "line_count": "正文行数（非空行）",
        "question_density_per_100_sentences": "问句密度 / 百句",
        "second_person_density_per_100_sentences": "第二人称密度 / 百句",
        "first_person_density_per_100_sentences": "第一人称密度 / 百句",
        "exclamation_density_per_1000_characters": "感叹号密度 / 千字",
        "emoji_count": "emoji 数量 / 篇",
        "emoji_density_per_100_characters": "emoji 密度 / 百字（正文）",
        "tag_count": "话题标签数 / 篇",
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
            "话题标签数按正文内联 `#话题` 统计；emoji 统计只作证据底座，不构成「必须凑满几个」的规则。",
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
        document = document_metrics(
            source_path,
            source_path.read_text(encoding="utf-8", errors="ignore"),
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
    if dimension["id"] == "cover-imageset":
        return (
            f"{heading}\n\n"
            "**视觉模型分析：**待 Agent 基于封面图（及图组图片，如有）补齐。\n\n"
            "- 封面承诺（用户点进来的可见理由）：待 Agent 补齐。\n"
            "- 版式与构图（大字报 / 实拍场景 / 对比图 / 清单卡片等）：待 Agent 补齐。\n"
            "- 色彩体系：待 Agent 补齐。\n"
            "- 文字视觉与图文关系（封面字 / 贴纸 / 标题框）：待 Agent 补齐。\n"
            "- 封面与图组的风格一致性：待 Agent 补齐。\n"
            "- 品牌识别元素：待 Agent 补齐。\n"
            "- 避免项：待 Agent 补齐。\n\n"
            "**AIGC 复现提示词要素：**待 Agent 补齐；要求能据此生成风格高度一致的封面图。\n\n"
            "**可复用创作信号：**待 Agent 补齐。"
        )
    if dimension["id"] == "opening-hook":
        return (
            f"{heading}\n\n"
            "**钩子原文（正文前 1-2 行）：**待 Agent 逐字摘录。\n\n"
            "**单条结论：**待 Agent 补齐（钩子类型、与封面承诺是否对应、正文是否兑现）。\n\n"
            "**原文证据：**待 Agent 补齐。\n\n"
            "**可复用创作信号：**待 Agent 补齐。"
        )
    if dimension["id"] == "image-composition":
        return (
            f"{heading}\n\n"
            "**图组清单与路径：**待 Agent 列出（没有图片时写「未提供」，不得编造）。\n\n"
            "**单条结论：**待 Agent 补齐（图片数量、构图类型分布、图文信息分工）。\n\n"
            "**原文证据：**待 Agent 补齐（逐图描述构图与信息点）。\n\n"
            "**可复用创作信号：**待 Agent 补齐。"
        )
    return (
        f"{heading}\n\n"
        "**单条结论：**待 Agent 补齐。\n\n"
        "**原文证据：**待 Agent 补齐（正文逐字引用或图片描述）。\n\n"
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
            f"weight: {weight}\n"
            f"focus: {yaml_value(focus)}\n"
            "sample_count: 1\n"
            f"generated_at: {yaml_value(generated_at())}\n"
            "---",
            f"# {document['title_candidates'][-1]} 单篇 DNA Report",
            "本文件只描述这一篇笔记。它不是聚合后的 DNA 文档，也不直接作为生产模板。",
            "## 单篇统计",
            f"- 总字符：{document['characters']}\n- 标题字数：{document['title_chars']}\n- 句子数：{document['sentences']}\n- 正文行数：{document['line_count']}\n- emoji 数：{document['emoji_count']}\n- 话题标签数：{document['tag_count']}\n- 标题候选：{' / '.join(document['title_candidates'])}\n- 来源链接：{source_url or '未提供'}\n- 封面图：{cover_image or '未提供'}",
            f"## {len(DIMENSIONS)} 维单篇分析",
            "\n\n".join(dimensions),
            "## 单篇边界",
            "- 这里记录本篇笔记的可复用信号，不判断跨篇稳定性。\n- 聚合时由 Agent 根据 DNA report、权重和 focus 判断共性、偏好和例外。",
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
            if dimension["id"] in ("cover-imageset", "image-composition"):
                dimensions.append(
                    f"{heading}\n\n**聚合结论：**待 Agent 补齐。\n\n"
                    "**报告依据：**待 Agent 列出使用的封面 / 图组图片和 DNA report。\n\n"
                    "**视觉生成规则：**待 Agent 转成可执行的 AIGC 提示词要素或配图规格。\n\n"
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
            "本文件聚合历史 DNA report。它是账号当前采用的小红书笔记内容与风格规则，也必须能推导出生产模板。",
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


TEMPLATE_STAGES = ("开头", "承", "结尾", "CTA", "图组")

TEMPLATE_STAGE_FIELDS = {
    "开头": (
        "本段任务",
        "钩子类型",
        "开头句式",
        "与封面承诺的兑现",
        "必须做",
        "避免",
    ),
    "承": (
        "本段任务",
        "推进逻辑",
        "信息密度",
        "段落与换行节奏",
        "emoji 使用",
        "证据与人味细节",
        "必须做",
        "避免",
    ),
    "结尾": (
        "本段任务",
        "收束方式",
        "情绪落点",
        "签名式标记",
        "必须做",
        "避免",
    ),
    "CTA": (
        "行动目标",
        "引导方式（评论/收藏/关注）",
        "平台内动作",
        "必须做",
        "避免",
    ),
    "图组": (
        "图片数量与顺序",
        "构图类型",
        "文字卡片设计",
        "风格一致性",
        "图文信息分工",
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
            # 只在真正的模板分段（[开头部分] 等）处截断；[标题] 属于选题与标题区，必须保留。
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
        "（封面图风格：待 Agent 补齐。）\n"
        "（封面 AIGC 提示词要素：待 Agent 补齐。）"
    )
    if previous_template:
        for field in ("（封面图风格：", "（封面 AIGC 提示词要素："):
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
            "- 开头、承、结尾、CTA、图组五个部分是否完成各自任务。\n"
            "- 每个部分是否反映 DNA 文档中对应的钩子、正文结构、语气、emoji 节奏、视觉、互动与签名标记。\n"
            "- 标题 ≤ 20 字、正文 ≤ 1000 字、图片 ≤ 18 张、话题标签 ≤ 10 个是否满足（平台硬限制）。\n"
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
            "本模板是小红书笔记生产时直接执行的 production template，必须由 DNA 文档推导；不得引入 DNA 文档未确认的规则。",
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
    paths = collect_input_paths(inputs_from_args(args), {".md", ".txt"})
    if len(paths) != 1:
        raise SystemExit("report command accepts exactly one note text; use build to aggregate reports")
    document = document_metrics(
        paths[0], paths[0].read_text(encoding="utf-8", errors="ignore")
    )
    output_dir = Path(args.output_dir or f"dna/xhs/{args.dna_id}/reports")
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
    print(f"Wrote single-note DNA report: {output}")


def build_command(args: argparse.Namespace) -> None:
    validate_id(args.dna_id, "--dna-id")
    input_values = args.input or [f"dna/xhs/{args.dna_id}/reports"]
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
    output_dir = Path(args.output_dir or f"dna/xhs/{args.dna_id}")
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
    parser = argparse.ArgumentParser(description="Build qualitative Xiaohongshu note DNA assets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Create one single-note DNA report")
    report.add_argument("--input", action="append", required=True)
    report.add_argument("--cover-image", help="Local cover image used by visual-model analysis")
    report.add_argument("--source-url", help="Original note URL kept as report evidence")
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
