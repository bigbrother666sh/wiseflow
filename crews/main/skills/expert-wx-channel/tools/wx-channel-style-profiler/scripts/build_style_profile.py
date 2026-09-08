#!/usr/bin/env python3
import argparse, json, math, re, shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


SENTENCE_SPLIT = re.compile(r"[。！？!?]+")
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
TOKEN_RE = re.compile(r"[一-鿿A-Za-z0-9_]+")
ENGLISH_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
SECOND_PERSON_RE = re.compile(r"你们?|you", re.IGNORECASE)
QUESTION_RE = re.compile(r"[？?]")
EXCLAMATION_RE = re.compile(r"[！!]")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
SOURCE_BLOCK_RE = re.compile(r"<!-- source-article\n(?P<path>.*?)\n-->", re.DOTALL)
REPORT_BLOCK_RE = re.compile(r"<!-- dna-reports\n(?P<paths>.*?)\n-->", re.DOTALL)

PLATFORM = "wx_channel"

STATISTICS_METRICS = [
    "avg_sentence_tokens",
    "avg_paragraph_tokens",
    "avg_sentences_per_paragraph",
    "question_density_per_100_sentences",
    "second_person_density_per_100_sentences",
    "exclamation_density_per_1000_characters",
]

STOP_TERMS = {
    "一个", "我们", "你们", "这里", "不会", "这个", "那个", "什么", "可以", "因为",
    "但是", "所以", "还是", "以及", "如果", "他们", "自己", "的时候", "to", "the",
    "a", "an", "is", "are", "and", "or", "of", "in", "for", "on", "with", "you", "we",
}

# DNA 维度 v1。调整维度需升版本，并同步 references/account-dna-framework.md 与 SKILL.md 的 Focus ID 表。
DIMENSION_GROUPS = {
    "定位与选题": [
        ("positioning-core", "定位与核心传达"),
        ("topic-portfolio", "选题组合"),
        ("description-packaging", "简介与包装"),
        ("bio-profile", "账号简介与主页表达"),
    ],
    "账号节奏": [
        ("content-form-mix", "内容形式与比例"),
        ("publish-cadence", "发布习惯"),
        ("high-performer-patterns", "高数据创意模式"),
    ],
    "表达与风格": [
        ("visual-language", "视觉语言"),
        ("audio-language", "声音语言"),
        ("narration-dna", "口播文案 DNA"),
    ],
    "互动与制作": [
        ("engagement-conversion", "互动与转化"),
        ("social-share-loop", "社交分享闭环"),
        ("series-signature", "系列与签名"),
        ("production-pipeline", "制作管线倾向"),
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

def split_paragraphs(text: str) -> list[str]:
    return [item.strip() for item in PARAGRAPH_SPLIT.split(text) if item.strip()]

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


def document_metrics(path: Path, text: str) -> dict:
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)
    sentence_lengths = [len(tokenize(sentence)) for sentence in sentences]
    paragraph_lengths = [len(tokenize(paragraph)) for paragraph in paragraphs]
    paragraph_sentence_counts = [max(len(split_sentences(paragraph)), 1) for paragraph in paragraphs]
    sentence_count = len(sentences)
    paragraph_count = len(paragraphs)
    character_count = len(text)

    return {
        "source_article": str(path.resolve()),
        "title_candidates": title_candidates(path, text),
        "characters": character_count,
        "sentences": sentence_count,
        "paragraphs": paragraph_count,
        "avg_sentence_tokens": average([float(value) for value in sentence_lengths]),
        "avg_paragraph_tokens": average([float(value) for value in paragraph_lengths]),
        "avg_sentences_per_paragraph": average([float(value) for value in paragraph_sentence_counts]),
        "question_density_per_100_sentences": safe_ratio(
            len(QUESTION_RE.findall(text)), sentence_count, 100
        ),
        "second_person_density_per_100_sentences": safe_ratio(
            len(SECOND_PERSON_RE.findall(text)), sentence_count, 100
        ),
        "exclamation_density_per_1000_characters": safe_ratio(
            len(EXCLAMATION_RE.findall(text)), character_count, 1000
        ),
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
        "avg_sentence_tokens": "平均句长（token）",
        "avg_paragraph_tokens": "平均每段/每镜长度（token）",
        "avg_sentences_per_paragraph": "平均每段/每镜句数",
        "question_density_per_100_sentences": "问句密度 / 百句",
        "second_person_density_per_100_sentences": "第二人称密度 / 百句",
        "exclamation_density_per_1000_characters": "感叹号密度 / 千字",
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
            f"样本覆盖度：`{statistics['report_count']}` 条 report；单条或少量样本不能推导账号比例、发布节奏或高数据共性。",
            f"权重模式：`{statistics['weighting']}`；总权重：`{statistics['total_weight']}`。",
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
        source_path = source_paths[0] if source_paths else Path(parse_quoted(metadata.get("source-article", "")))
        if not source_path.is_file():
            raise SystemExit(f"DNA report source article does not exist: {source_path}")
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


REPORT_DIMENSION_PROMPTS = {
    'positioning-core': '- 单条观测：本条暴露出的定位、目标人群与核心传达。\n- 账号级判断：单条样本只给候选，不直接判定账号稳定性。',
    'topic-portfolio': '- 单条观测：本条选题类型、入口和系列关系。',
    'description-packaging': '- 单条观测：视频简介 / 封面 / 话题标签包装模式；只记模式，不抄成固定字句。',
    'bio-profile': '- 账号级观测：账号简介、主页与置顶表达；单条样本无法观测时写未观测。',
    'content-form-mix': '- 单条观测：本条内容形式。\n- 聚合边界：图文/视频比例与混合节奏必须由多样本或账号级数据推导。',
    'publish-cadence': '- 单条观测：本条发布时间。\n- 聚合边界：时间段、频率和三图文对一视频等节奏必须由多样本或账号级数据推导。',
    'high-performer-patterns': '- 数据线索：记录本条互动/播放/阅读线索。\n- 创意判断：回读选题、包装、形式与创意，不得把高数据直接等同于风格好。',
    'visual-language': '- 视觉证据：有图片或关键帧时由视觉模型读取；无证据写未观测。\n- 边界：只记录账号级稳定视觉语言，不规定逐镜设计。',
    'audio-language': '- 声音证据：来自口播稿、原视频信息或用户说明；无证据写未观测。\n- 边界：只记录音色/语速/声音气质倾向，不规定 TTS 参数。',
    'narration-dna': '- 独立块：记录开头、起承转合、收束、人称与签名表达。\n- 聚合边界：样本不足时保持未启用，不把单条句式上升为账号 DNA。',
    'engagement-conversion': '- 单条观测：平台内行动引导与承接路径。',
    'social-share-loop': '- 单条观测：转发动机、分享话术和被转发后的承接。',
    'series-signature': '- 单条观测：栏目、固定表达或识别符号；高频词必须回读原文确认。',
    'production-pipeline': '- 管线映射：只写 Content Producer 已支持的 Pipeline；未确定时写待定。\n- 分界：DNA 指导 main agent 出 Brief，不规定成片制作细节。',
}

def report_dimension_markdown(dimension: dict) -> str:
    heading = f"### {dimension['number']}. {dimension['name']}"
    prompt = REPORT_DIMENSION_PROMPTS.get(dimension["id"], "- 单条观测：待 Agent 补齐。")
    return (
        f"{heading}\n\n"
        f"{prompt}\n\n"
        "**单条结论：**待 Agent 补齐。\n\n"
        "**原文证据：**待 Agent 补齐（逐字引用、账号信息、发布信息、画面/声音描述或数据线索；注明来源）。\n\n"
        "**可复用信号：**待 Agent 补齐；样本不足时写未观测，不推导账号级稳定性。"
    )


def report_markdown(
    dna_id: str,
    report_id: str,
    weight: float,
    focus: list[str],
    document: dict,
    cover_image: str,
    source_video: str,
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
            f"source-article: {yaml_value(document['source_article'])}\n"
            f"source-video: {yaml_value(source_video)}\n"
            f"cover-image: {yaml_value(cover_image)}\n"
            f"weight: {weight}\n"
            f"focus: {yaml_value(focus)}\n"
            "sample_count: 1\n"
            f"generated_at: {yaml_value(generated_at())}\n"
            "---",
            f"# {document['title_candidates'][-1]} 单条视频 DNA Report",
            "本文件只描述这一条视频。它不是聚合后的 DNA 文档，也不直接作为创作模板。",
            "## 单篇统计",
            f"- 字符：{document['characters']}\n- 句子：{document['sentences']}\n- 段落/镜次：{document['paragraphs']}\n- 简介摘要候选：{' / '.join(document['title_candidates'])}\n- 封面图：{cover_image or '未提供'}\n- 源视频：{source_video or '未提供'}",
            "## 视频信息（待 Agent 结合原视频 / 用户提供信息补齐）",
            "- 时长：待 Agent 补齐。\n- 视频形态：待 Agent 补齐（竖屏/横屏，真人出镜 / 配音解说 / 素材剪辑 / AIGC）。\n- 真人出镜占比：待 Agent 补齐。\n- 镜头与字幕要点：待 Agent 补齐。\n- BGM 与音效：待 Agent 补齐。\n- 数据线索（可选，播放 / 互动等）：待 Agent 补齐，不得编造。",
            "## 样本与账号观测",
            '- 样本类型：待 Agent 补齐（账号作品 / 用户提供单条）。\n- 账号与简介：待 Agent 补齐；单条样本无法观测时写未观测。\n- 发布时间与时间段：待 Agent 补齐；单条样本只记录本条时间，不推导账号节奏。\n- 内容形式：待 Agent 补齐（口播 / 实拍拼接 / 创意转场 / 纯 AIGC 动画 / 图文 / 混合）。\n- 数据表现线索：待 Agent 补齐；只作证据，不直接判风格好坏。\n- 视频形态与授权信息：待 Agent 补齐（横竖屏、时长、素材来源、授权边界）。',
            f"## {len(DIMENSIONS)} 维单篇分析",
            "\n\n".join(dimensions),
            "## 单篇边界",
            "- 这里记录本条视频的可复用信号，不判断跨篇稳定性。\n- 聚合时由 Agent 根据 DNA report、权重和 focus 判断共性、偏好和例外。",
            f"<!-- source-article\n{document['source_article']}\n-->",
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
            "本文件聚合历史 DNA report。它是账号/作者当前采用的视频号内容风格与选题规则，也必须能推导出生产模板。",
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


TEMPLATE_STAGES = ("定位与核心传达", "选题与简介包装", "内容形式与发布节奏", "高数据创意模式", "互动与系列", "制作交接与Pipeline", "口播文案DNA")

TEMPLATE_STAGE_FIELDS = {
    "定位与核心传达": (
        "一句话定位",
        "目标人群",
        "核心传达",
        "账号简介与主页表达",
        "不变承诺",
    ),
    "选题与简介包装": (
        "选题组合",
        "视频简介模式",
        "封面包装",
        "禁用方向",
    ),
    "内容形式与发布节奏": (
        "图文或视频比例",
        "发布时间带",
        "内容形式混合节奏",
        "系列栏目",
    ),
    "高数据创意模式": (
        "高表现样本共性",
        "可复用创意原型",
        "触发条件",
        "例外",
    ),
    "互动与系列": (
        "互动目标",
        "引导方式",
        "社交分享动机",
        "系列与签名标记",
        "必须做",
        "避免",
    ),
    "制作交接与Pipeline": (
        "MainAgent交付物",
        "ContentProducer交付物",
        "Pipeline",
        "素材与授权",
        "风格边界",
    ),
    "口播文案DNA": (
        "是否启用",
        "起承转合结构",
        "语言与人称",
        "声音倾向",
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
    section_defaults = [
        (
            "## 生产模板",
            "\n\n".join(segments),
        ),
        (
            "## 用户输入转译后的执行规则",
            "- （来自用户输入：待 Agent 补齐来源。）\n"
            f"- （影响维度：待 Agent 映射到 {len(DIMENSIONS)} 维 ID。）\n"
            "- （执行规则：待 Agent 写成 Brief 或图文生产时可直接执行的要求。）",
        ),
        (
            "## 使用检查",
            "- 是否只用一个 DNA，且与本次账号 / 内容任务匹配。\n"
            "- 定位、选题、视频简介包装、核心传达是否来自 DNA 文档。\n"
            "- 图文/视频比例、发布节奏和高数据创意是否尊重样本覆盖度；样本不足时是否标注未观测。\n"
            "- 视频全案是否只输出 Brief，且 Brief 明确 Pipeline、素材授权、验收标准和交付边界。\n"
            "- 口播文案 DNA 是否独立启用；未启用时是否避免规定逐句口播。\n"
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
            "本模板是 main agent 的账号级内容生产 / Brief 输入模板，必须由 DNA 文档推导；不得引入 DNA 文档未确认的规则，也不规定成片制作细节。",
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
        raise SystemExit("report command accepts exactly one script/transcript; use build to aggregate reports")
    document = document_metrics(
        paths[0], paths[0].read_text(encoding="utf-8", errors="ignore")
    )
    output_dir = Path(args.output_dir or f"{PLATFORM}/dna/{args.dna_id}/reports")
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
            args.source_video or "",
        ),
    )
    print(f"Wrote single-video DNA report: {output}")


def build_command(args: argparse.Namespace) -> None:
    validate_id(args.dna_id, "--dna-id")
    input_values = args.input or [f"{PLATFORM}/dna/{args.dna_id}/reports"]
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
    output_dir = Path(args.output_dir or f"{PLATFORM}/dna/{args.dna_id}")
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
    parser = argparse.ArgumentParser(description="Build qualitative WeChat Channels (视频号) video DNA assets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Create one single-video DNA report")
    report.add_argument("--input", action="append", required=True)
    report.add_argument("--cover-image", help="Local cover image used by visual-model analysis")
    report.add_argument("--source-video", help="Optional source video URL or local path, recorded in frontmatter")
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
