#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import median


SENTENCE_SPLIT = re.compile(r"[。！？!?]+")
TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9_]+")
ENGLISH_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
SECOND_PERSON_RE = re.compile(r"你们?|you", re.IGNORECASE)
FIRST_PERSON_PLURAL_RE = re.compile(r"我们|we", re.IGNORECASE)
QUESTION_RE = re.compile(r"[？?]")
EXCLAMATION_RE = re.compile(r"[！!]")
EM_DASH_RE = re.compile(r"──|—|–")

EVALUATED_METRICS = [
    "avg_sentence_tokens",
    "avg_paragraph_tokens",
    "avg_sentences_per_paragraph",
    "question_density_per_100_sentences",
    "second_person_density_per_100_sentences",
    "first_person_plural_density_per_100_sentences",
    "em_dash_density_per_1000_characters",
    "exclamation_density_per_1000_characters",
]

STOP_TERMS = {
    "一个", "我们", "你们", "这里", "不会", "这个", "那个", "什么", "可以", "因为",
    "但是", "所以", "还是", "以及", "如果", "他们", "自己", "的时候", "to", "the",
    "a", "an", "is", "are", "and", "or", "of", "in", "for", "on", "with", "you", "we",
}

DNA_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def split_sentences(text: str) -> list[str]:
    return [item.strip() for item in SENTENCE_SPLIT.split(text) if item.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]


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
        "file": path.name,
        "characters": character_count,
        "sentences": sentence_count,
        "paragraphs": paragraph_count,
        "avg_sentence_tokens": average([float(value) for value in sentence_lengths]),
        "avg_paragraph_tokens": average([float(value) for value in paragraph_lengths]),
        "avg_sentences_per_paragraph": average([float(value) for value in paragraph_sentence_counts]),
        "paragraphs_over_3_sentences_ratio": safe_ratio(
            sum(value > 3 for value in paragraph_sentence_counts), paragraph_count
        ),
        "question_density_per_100_sentences": safe_ratio(
            len(QUESTION_RE.findall(text)), sentence_count, 100
        ),
        "second_person_density_per_100_sentences": safe_ratio(
            len(SECOND_PERSON_RE.findall(text)), sentence_count, 100
        ),
        "first_person_plural_density_per_100_sentences": safe_ratio(
            len(FIRST_PERSON_PLURAL_RE.findall(text)), sentence_count, 100
        ),
        "em_dash_density_per_1000_characters": safe_ratio(
            len(EM_DASH_RE.findall(text)), character_count, 1000
        ),
        "exclamation_density_per_1000_characters": safe_ratio(
            len(EXCLAMATION_RE.findall(text)), character_count, 1000
        ),
        "terms": dict(extract_terms(text)),
    }


def read_documents(input_dir: Path) -> list[dict]:
    files = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}
    )
    return [document_metrics(path, path.read_text(encoding="utf-8", errors="ignore")) for path in files]


def median_absolute_deviation(values: list[float], center: float) -> float:
    return rounded(median(abs(value - center) for value in values)) if values else 0.0


def aggregate_numeric_metrics(documents: list[dict]) -> dict:
    aggregated = {}
    for metric_name in EVALUATED_METRICS:
        values = [float(document[metric_name]) for document in documents]
        center = rounded(median(values)) if values else 0.0
        aggregated[metric_name] = {
            "median": center,
            "mad": median_absolute_deviation(values, center),
            "min": rounded(min(values)) if values else 0.0,
            "max": rounded(max(values)) if values else 0.0,
        }
    return aggregated


def aggregate_terms(documents: list[dict], limit: int = 30) -> list[dict]:
    document_count = len(documents)
    if not document_count:
        return []
    frequencies = []
    for document in documents:
        for term, count in document["terms"].items():
            frequencies.append((term, count))

    grouped: dict[str, list[int]] = {}
    for term, count in frequencies:
        grouped.setdefault(term, []).append(count)
    minimum_frequency = max(2, math.ceil(document_count * 0.6))
    stable = [
        {
            "term": term,
            "document_frequency": len(counts),
            "document_frequency_ratio": rounded(len(counts) / document_count),
            "median_count_per_document": rounded(median(counts)),
            "total_count": sum(counts),
        }
        for term, counts in grouped.items()
        if len(counts) >= minimum_frequency
    ]
    stable.sort(
        key=lambda item: (
            item["document_frequency"],
            item["median_count_per_document"],
            item["total_count"],
        ),
        reverse=True,
    )
    return stable[:limit]


def confidence_for(document_count: int) -> str:
    if document_count >= 10:
        return "high"
    if document_count >= 5:
        return "medium"
    return "low"


def evaluation_tolerance(target: float, mad: float) -> float:
    return max(mad * 1.5, abs(target) * 0.25, 0.01)


def dimension_score(observed: float, target: float, tolerance: float) -> float:
    difference = abs(observed - target)
    if difference <= tolerance:
        return 100.0
    falloff = min((difference - tolerance) / (tolerance * 2), 1)
    return rounded(100 * (1 - falloff))


def build_profile(input_dir: Path, dna_id: str, author: str) -> dict:
    documents = read_documents(input_dir)
    document_count = len(documents)
    if document_count < 3:
        raise SystemExit("Need at least 3 sample files (.txt/.md) to build a statistical DNA")

    return {
        "schema_version": 1,
        "dna_id": dna_id,
        "author": author,
        "sample_summary": {
            "document_count": document_count,
            "confidence": confidence_for(document_count),
            "confidence_rule": "high >=10; medium 5-9; low 3-4",
        },
        "statistical_method": {
            "unit": "document",
            "aggregation": "per-document metric first, then median and MAD across documents",
            "stable_feature_rule": "qualitative feature requires evidence in at least 60% documents and no recent trend reversal",
            "weighting": "none: wx_mp public reading metrics from competitor articles are unavailable",
        },
        "numeric_metrics": aggregate_numeric_metrics(documents),
        "signatures": {"terms": aggregate_terms(documents)},
        "documents": documents,
        "evaluation_contract": {
            "metrics": EVALUATED_METRICS,
            "target": "median",
            "tolerance": "max(1.5 * MAD, 25% of target, 0.01)",
            "dimension_score": "100 inside tolerance; linear falloff to 0 at 3x tolerance",
            "overall_pass_score": 80,
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def metric_lines(profile: dict) -> str:
    lines = []
    labels = {
        "avg_sentence_tokens": "句长（token）",
        "avg_paragraph_tokens": "段落长度（token）",
        "avg_sentences_per_paragraph": "每段句数",
        "question_density_per_100_sentences": "问句密度（/百句）",
        "second_person_density_per_100_sentences": "第二人称密度（/百句）",
        "first_person_plural_density_per_100_sentences": "我们密度（/百句）",
        "em_dash_density_per_1000_characters": "破折号密度（/千字）",
        "exclamation_density_per_1000_characters": "感叹号密度（/千字）",
    }
    for metric_name, label in labels.items():
        values = profile["numeric_metrics"][metric_name]
        lines.append(
            f"- {label}：目标中位数 {values['median']}，可接受波动约 ±{evaluation_tolerance(values['median'], values['mad'])}"
        )
    return "\n".join(lines)


def write_instruction(path: Path, profile: dict) -> None:
    terms = [item["term"] for item in profile["signatures"]["terms"][:8]]
    content = f"""---
dna-id: {profile['dna_id']}
domain: wx-mp
type: content-style
label: {profile['author']}
source: statistical-style-profile
confidence: {profile['sample_summary']['confidence']}
evaluation: {path.stem}.evaluation.md
metrics: {path.stem}.metrics.json
---

# {profile['author']} 公众号内容生产 Instruction

## 使用时必须执行

1. 写前读取本文件的量化目标和 14 维判断；不得只凭印象仿写。
2. 结构、开头、论证、收束、CTA 按 14 维稳定共性执行；每个定性判断必须能指出样本证据。
3. 覆盖样本中重复出现的表达动作，不机械堆砌高频词。
4. 写完运行配套 evaluation 命令，得分低于 80 或关键维度为 0 时先修订再交付。
5. 排版主题独立选择；不得把排版变化解释为 DNA 符合或不符合。

## 可观测量化目标

{metric_lines(profile)}

## 稳定表达信号

{", ".join(terms) if terms else "样本中未提取到跨篇稳定词"}

## 14 维执行区

> 工具先生成统计底座；agent 结合原文证据补齐以下直接指令，不用空泛形容词。

1. 用词习惯：
2. 词汇与句式：
3. 句式节奏：
4. 语气与基调：
5. 段落结构：
6. 文章结构模式：
7. 论证逻辑：
8. 节奏感：
9. 修辞手法：
10. 情感表达：
11. 思维特征：
12. 专业度体现：
13. 签名式标记：
14. 起承转合微操：

## 例外与低置信提示

- 样本数：{profile['sample_summary']['document_count']}，置信度：{profile['sample_summary']['confidence']}。
- 低置信 DNA 只能作为草稿基线，后续补足样本后重建。
- 单篇孤例只能记录在例外区，不得进入稳定 DNA。
"""
    path.write_text(content, encoding="utf-8")


def write_evaluation(path: Path, profile: dict) -> None:
    content = f"""# {profile['author']} 公众号 DNA 可观测评估

## 使用规则

- 生产前遵循 `{path.stem.replace(".evaluation", "")}.md`。
- 生产后必须计算本文件；总分低于 80 时不交付。
- 分数衡量内容风格相似度，不衡量合规性、事实准确性或商业质量。

## 计算命令

```bash
wechat-style-profiler evaluate --metrics {path.stem.replace(".evaluation", "")}.metrics.json --article <article.md> --output <article-dna-evaluation.json>
```

## 可观测维度

{metric_lines(profile)}

## 评分

- 每个数值维度先计算稿件指标，再与样本中位数比较。
- 容差：`max(1.5 × MAD, 25% × 目标值, 0.01)`。
- 容差内 100 分；超出后线性下降，到 3 倍容差为 0。
- 稳定表达信号按覆盖率计分。
- 总分为维度加权平均，通过线 80 分。
"""
    path.write_text(content, encoding="utf-8")


def evaluate_article(profile: dict, article_path: Path) -> dict:
    draft = document_metrics(article_path, article_path.read_text(encoding="utf-8", errors="ignore"))
    dimensions = []
    for metric_name in EVALUATED_METRICS:
        values = profile["numeric_metrics"][metric_name]
        target = float(values["median"])
        observed = float(draft[metric_name])
        tolerance = evaluation_tolerance(target, float(values["mad"]))
        dimensions.append(
            {
                "metric": metric_name,
                "target": target,
                "tolerance": tolerance,
                "observed": observed,
                "difference_from_target": rounded(observed - target),
                "score": dimension_score(observed, target, tolerance),
            }
        )

    signature_terms = [item["term"] for item in profile["signatures"]["terms"][:5]]
    if signature_terms:
        draft_terms = set(draft["terms"])
        covered = sum(term in draft_terms for term in signature_terms)
        dimensions.append(
            {
                "metric": "stable_signature_term_coverage",
                "target": len(signature_terms),
                "tolerance": 0,
                "observed": covered,
                "difference_from_target": covered - len(signature_terms),
                "score": rounded(100 * covered / len(signature_terms)),
            }
        )

    overall = rounded(sum(item["score"] for item in dimensions) / len(dimensions))
    return {
        "schema_version": 1,
        "dna_id": profile["dna_id"],
        "article": str(article_path),
        "overall_score": overall,
        "passed": overall >= profile["evaluation_contract"]["overall_pass_score"],
        "dimension_count": len(dimensions),
        "dimensions": dimensions,
    }


def build_command(args: argparse.Namespace) -> None:
    if not DNA_ID_RE.fullmatch(args.dna_id):
        raise SystemExit("--dna-id must be 2-64 chars: lowercase letters, digits, and hyphens")
    profile = build_profile(Path(args.input_dir), args.dna_id, args.author)
    output_dir = Path(args.output_dir)
    write_json(output_dir / f"{args.dna_id}.metrics.json", profile)
    write_instruction(output_dir / f"{args.dna_id}.md", profile)
    write_evaluation(output_dir / f"{args.dna_id}.evaluation.md", profile)
    print(f"Wrote statistical DNA to {output_dir}")


def evaluate_command(args: argparse.Namespace) -> None:
    profile = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    report = evaluate_article(profile, Path(args.article))
    write_json(Path(args.output), report)
    status = "PASS" if report["passed"] else "FAIL"
    print(f"DNA evaluation {status}: {report['overall_score']} -> {args.output}")
    if not report["passed"]:
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and evaluate WeChat MP statistical style DNA")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build instruction, evaluation, and metrics from samples")
    build.add_argument("--input-dir", required=True)
    build.add_argument("--dna-id", required=True)
    build.add_argument("--author", required=True)
    build.add_argument("--output-dir", default="dna/wx_mp")
    build.set_defaults(handler=build_command)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate one article against metrics")
    evaluate.add_argument("--metrics", required=True)
    evaluate.add_argument("--article", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.set_defaults(handler=evaluate_command)
    return parser


def run(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    run()
