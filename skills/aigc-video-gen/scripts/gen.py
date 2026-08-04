#!/usr/bin/env python3
"""Video AIGC generation — direct endpoint calls to Volcengine Seedance or Aliyun DashScope.

Stdlib only (no httpx/requests). The script auto-detects which platform to use
from environment variables (DashScope/百炼 preferred over Volcengine/火山), submits
an async video-generation task, polls until completion, and downloads the MP4.

Flow:
  1. Resolve platform (override via --platform, else env vars)
  2. Resolve mode: r2v (ref-image/ref-video) > i2v (image) > t2v
  3. Pick model: --model, else platform candidate chain (with fallback)
  4. POST create task → task_id
  5. Poll task status until terminal
  6. Download video_url → --output

If neither MODELSTUDIO_API_KEY/DASHSCOPE_API_KEY nor AWK_GEN_KEY is set,
prints guidance to use pexels-footage / pixabay-footage and exits non-zero.

Note: 火山引擎视频生成只认 AWK_GEN_KEY，不回退 ARK_API_KEY。
原因：ARK_API_KEY 是火山主模型（doubao 对话）的 key，用户可能只想用火山主模型
而不用火山生成视频；若此处回退 ARK_API_KEY，会误触发火山视频生成。
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---- Volcengine Ark (Seedance) -------------------------------------------------
VOLC_BASE = "https://ark.cn-beijing.volces.com/api/v3"
VOLC_CREATE = f"{VOLC_BASE}/contents/generations/tasks"
VOLC_QUERY = f"{VOLC_BASE}/contents/generations/tasks/{{task_id}}"

# Seedance 2.0 series. Fast preferred → normal → mini. All three are multimodal
# (t2v / i2v / r2v share the same model id).
VOLC_MODELS = {
    "fast": "doubao-seedance-2-0-fast-260128",
    "normal": "doubao-seedance-2-0-260128",
    "mini": "doubao-seedance-2-0-mini-260615",
}

# ---- Aliyun DashScope (百炼 Wan2.7 / HappyHorse) ------------------------------
# wan2.7 走默认 dashscope 端点；HappyHorse 是华北2模型，配了 WORKSPACE_ID 时走业务空间
# 专属端点 https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com（见 SKILL.md 模型选型）。
DS_DEFAULT_BASE = "https://dashscope.aliyuncs.com/api/v1"
DS_WS_BASE_TEMPLATE = "https://{wsid}.cn-beijing.maas.aliyuncs.com/api/v1"
DS_CREATE_PATH = "/services/aigc/video-generation/video-synthesis"
DS_QUERY_PATH = "/tasks/{task_id}"


def ds_base_for_model(model: str) -> str:
    """Resolve the DashScope base URL for a given model.

    happyhorse-1.1 / 1.0 在默认 dashscope.aliyuncs.com 端点可正常调用（WorkspaceId 端点
    只是华北2的性能优化，非必需）。WORKSPACE_ID 设置时走专属端点更快，否则走默认。
    wan2.7 始终走默认端点。
    """
    wsid = (os.environ.get("WORKSPACE_ID") or "").strip()
    if model.startswith("happyhorse") and wsid:
        return DS_WS_BASE_TEMPLATE.format(wsid=wsid)
    return DS_DEFAULT_BASE

# 百炼模型候选链（按价格/可用性优先，每模式一条）：
#   happyhorse-1.1 系列（当前折扣价低于 wan2.7，优先）→ happyhorse-1.0 系列 → wan2.7 系列托底
# generate() 在 TaskFailed / HttpError 时自动沿链 fallback；--model 显式指定时只用该模型。
DS_MODEL_CHAIN = {
    "t2v": ["happyhorse-1.1-t2v", "happyhorse-1.0-t2v", "wan2.7-t2v"],
    "i2v": ["happyhorse-1.1-i2v", "happyhorse-1.0-i2v", "wan2.7-i2v"],
    "r2v": ["happyhorse-1.1-r2v", "happyhorse-1.0-r2v", "wan2.7-r2v"],
}

VALID_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}
SAFE_OUTPUT_DIRS = (
    Path("output_videos"),
    Path("tmp"),
    Path("fragments"),
    Path("artifacts"),
)

# Transient HTTP statuses worth retrying on the same model before falling back.
RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}

# Poll cadence / overall timeout for task polling (agent 不调，固定常量)
VOLC_POLL_INTERVAL = 15
VOLC_TIMEOUT = 900
DS_POLL_INTERVAL = 15
DS_TIMEOUT = 900


def die(message: str, code: int = 1) -> None:
    print(f"[error] {message}", file=sys.stderr)
    sys.exit(code)


def log(message: str) -> None:
    print(f"[info] {message}")


def append_decision(entry: str) -> None:
    """候选链 fallback 或全失败时往 decisions.log 追一行（借鉴 OpenMontage decision_log).

    落点：workdir 下 decisions.log（gen.py 的 workdir 由 ensure_safe_output 约束在 workspace 根，
    decisions.log 同落那）。append-only，不动旧内容。格式：ISO 时间 | 事件 | 详情。
    落盘失败不阻塞主流程——decisions.log 是审计辅助，不是硬约束。
    """
    try:
        from datetime import datetime
        ts = datetime.now().astimezone().isoformat(timespec="seconds")
        line = f"{ts} | {entry}\n"
        with Path("decisions.log").resolve().open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ---- asset resolution ---------------------------------------------------------

def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def image_to_data_url(path: Path) -> str:
    """Base64-encode a local image into a data: URL acceptable by both platforms."""
    if not path.is_file():
        die(f"image file not found: {path}")
    mime, _ = mimetypes.guess_type(str(path))
    if not mime or not mime.startswith("image/"):
        die(f"unsupported image type: {path}")
    raw = path.read_bytes()
    if len(raw) > 30 * 1024 * 1024:
        die(f"image exceeds 30MB: {path}")
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def resolve_image(value: str) -> str:
    """Images may be a public URL or a local file (base64 data URL)."""
    if is_url(value):
        return value
    return image_to_data_url(Path(value))


# ---- prev-segment last-frame extraction ---------------------------------------

def ffprobe_duration(path: Path) -> float:
    """Get media duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_entries", "format=duration", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0) or 0)
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError) as exc:
        die(f"ffprobe failed on {path}: {exc}")


def extract_last_frame(video_path: Path) -> Path:
    """Extract the last frame of a video to a sibling hidden .jpg.

    Used by --prev-segment: the last frame of the previous segment becomes the
    first frame of the next segment, giving首尾帧对齐 between人物故事片段.
    Output is a .jpg sibling of the source (assemble.py only picks video
    extensions, so this never pollutes the concat order).

    Strategy: try multiple ffmpeg seek strategies in order. Some AI-generated
    videos (notably 百炼 wan2.7-r2v) produce MP4s where the container duration
    is slightly larger than the actual stream end — e.g. duration=10.030998s but
    the last frame is at 9.967s (300 frames @ 30fps). A naive output-side
    `-ss duration - 0.05` then lands past the last frame and ffmpeg reports
    "Output file is empty, nothing was encoded". We try three strategies in
    order and use the first one that produces a non-empty jpg:
      1) `-sseof -1` + `-update 1` (seek-from-end, gives the actual last frame
         for any video ≥1s; the image2 muxer keeps overwriting the single jpg
         with each decoded frame and ends on the final one)
      2) `-ss duration - 0.5` (more conservative from-start accurate seek;
         decodes from 0 but lands well before any "container padding")
      3) `-ss duration - 1.0` (last resort; near-end frame)
    """
    if not video_path.is_file():
        die(f"--prev-segment video not found: {video_path}")
    duration = ffprobe_duration(video_path)
    if duration <= 0:
        die(f"could not determine duration for --prev-segment video: {video_path}")
    dest = video_path.with_name(f".{video_path.stem}_lastframe.jpg")
    # Clean up any stale file from a previous failed attempt
    if dest.is_file():
        dest.unlink()

    strategies: list[tuple[str, list[str]]] = [
        (
            "-sseof -1 (seek-from-end)",
            [
                "ffmpeg", "-y", "-sseof", "-1", "-i", str(video_path),
                "-update", "1", "-frames:v", "1", "-q:v", "2", "-an", str(dest),
            ],
        ),
        (
            f"-ss {max(0.0, duration - 0.5):.3f} (duration - 0.5s)",
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-ss", f"{max(0.0, duration - 0.5):.3f}",
                "-frames:v", "1", "-q:v", "2", "-an", str(dest),
            ],
        ),
        (
            f"-ss {max(0.0, duration - 1.0):.3f} (duration - 1.0s)",
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-ss", f"{max(0.0, duration - 1.0):.3f}",
                "-frames:v", "1", "-q:v", "2", "-an", str(dest),
            ],
        ),
    ]

    attempts: list[str] = []
    for label, cmd in strategies:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            attempts.append(f"[{label}] ffmpeg timed out after 60s")
            continue
        if (
            result.returncode == 0
            and dest.is_file()
            and dest.stat().st_size > 0
        ):
            log(
                f"extracted last frame of {video_path.name} → {dest.name} "
                f"(strategy: {label})"
            )
            return dest
        tail = (result.stderr or "")[-300:]
        attempts.append(
            f"[{label}] rc={result.returncode} "
            f"dest_exists={dest.is_file()} tail={tail!r}"
        )
        # Clean up partial/empty output before next attempt
        if dest.is_file():
            dest.unlink()

    die(
        f"ffmpeg last-frame extraction failed on {video_path} "
        f"(tried {len(strategies)} strategies):\n"
        + "\n".join(attempts)
    )


def resolve_media_url(value: str, kind: str) -> str:
    """Video/audio references must be public URLs — neither platform accepts
    base64 for video/audio in a way we can reliably use, so require a URL."""
    if is_url(value):
        return value
    die(
        f"--{kind} must be a public http(s) URL; local {kind} files are not "
        f"supported (upload to OSS/TOS/a public host first). Got: {value}"
    )


def ensure_safe_output(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        die(f"--output must be relative to the workspace: {raw_path}")
    if ".." in path.parts:
        die(f"--output must not contain '..': {raw_path}")
    root = Path.cwd().resolve()
    resolved = (root / path).resolve()
    if not any(
        resolved.is_relative_to((root / base).resolve()) for base in SAFE_OUTPUT_DIRS
    ):
        die(
            f"--output must be under one of: {', '.join(str(d) for d in SAFE_OUTPUT_DIRS)}"
        )
    return resolved


# ---- HTTP helpers -------------------------------------------------------------

def post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise HttpError(exc.code, body) from None
    except urllib.error.URLError as exc:
        raise HttpError(0, str(exc.reason)) from None


def get_json(url: str, headers: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise HttpError(exc.code, body) from None
    except urllib.error.URLError as exc:
        raise HttpError(0, str(exc.reason)) from None


class HttpError(Exception):
    def __init__(self, code: int, body: str):
        super().__init__(f"HTTP {code}: {body}")
        self.code = code
        self.body = body


def download(url: str, dest: Path, timeout: int = 300) -> None:
    log(f"downloading → {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "wiseflow-video-gen/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


# ---- platform: Volcengine -----------------------------------------------------

def volc_build_content(args: argparse.Namespace) -> list[dict]:
    items: list[dict] = [{"type": "text", "text": args.prompt}]
    if args.image:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.image)}, "role": "first_frame"}
        )
    if args.last_frame:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.last_frame)}, "role": "last_frame"}
        )
    if args.ref_image:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.ref_image)}, "role": "reference_image"}
        )
    if args.ref_video:
        items.append(
            {"type": "video_url", "video_url": {"url": resolve_media_url(args.ref_video, "ref-video")}}
        )
    return items


def volc_submit(model: str, args: argparse.Namespace, api_key: str) -> str:
    payload: dict = {
        "model": model,
        "content": volc_build_content(args),
        "ratio": args.ratio,
        "duration": args.duration,
        "resolution": args.resolution.lower(),
        "generate_audio": args.audio,
        "watermark": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = post_json(VOLC_CREATE, payload, headers, timeout=60)
    task_id = resp.get("id") or resp.get("task_id")
    if not task_id:
        die(f"volcengine submit: no task id in response: {json.dumps(resp, ensure_ascii=False)}")
    return task_id


def volc_poll(task_id: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = VOLC_QUERY.format(task_id=task_id)
    deadline = time.time() + VOLC_TIMEOUT
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        resp = get_json(url, headers, timeout=30)
        status = resp.get("status", "")
        log(f"volc poll #{attempt}: status={status}")
        if status == "succeeded":
            video_url = (resp.get("content") or {}).get("video_url")
            if not video_url:
                die(f"volcengine succeeded but no video_url: {json.dumps(resp, ensure_ascii=False)}")
            return video_url
        if status in {"failed", "cancelled", "expired"}:
            err = resp.get("error") or {}
            raise TaskFailed(f"volcengine task {status}: {err.get('code', '')} {err.get('message', '')}")
        time.sleep(VOLC_POLL_INTERVAL)
    die(f"volcengine timed out after {VOLC_TIMEOUT}s (task {task_id})")


# ---- platform: MiniMax (Hailuo-H3 video + music) ------------------------------
# 官方文档:
#   视频生成 V2: https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create
#   音乐生成:    https://platform.minimaxi.com/docs/api-reference/music-generation
#
# 视频生成走 V2 异步任务模型:
#   POST /v2/video_generation          → 创建任务,返回 task_id
#   GET  /v2/query/video_generation/{task_id}  → 轮询 task.status
#   成功时 task.content.url 即成片下载地址(无需 file_id / files/retrieve 换链)。
# 请求体用 content[] 多模态数组,每个元素 type(text/image_url/video_url/audio_url)
# + role(first_frame/last_frame/reference_image/reference_video/reference_audio)。
#
# 音乐生成走 /v1/music_generation,官方示例为同步 POST 直接返回结果。
#
# 鉴权:HTTP header `Authorization: Bearer ${MINIMAX_API_KEY}`。
MM_BASE = "https://api.minimaxi.com"
MM_VIDEO_CREATE = f"{MM_BASE}/v2/video_generation"
MM_VIDEO_QUERY = f"{MM_BASE}/v2/query/video_generation/{{task_id}}"
MM_MUSIC_CREATE = f"{MM_BASE}/v1/music_generation"

# MiniMax 视频模型候选链(质量优先 → 速度/兜底)
# 主力 MiniMax-H3;兜底暂留 MiniMax-H3(官方文档示例仅 H3,无其他可选项披露)。
MM_VIDEO_MODELS = {
    "hailuo-h3": "MiniMax-H3",
}
MM_MUSIC_MODEL = "music-3.0"

MM_POLL_INTERVAL = 10  # 官方推荐轮询间隔 10 秒
MM_TIMEOUT = 900


def mm_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def mm_video_build_content(model: str, args: argparse.Namespace) -> list[dict]:
    """构造 MiniMax V2 视频 content[] 数组。

    模式映射(与百炼/火山对齐):
      - t2v: 纯 prompt 文本
      - i2v: prompt + first_frame image
      - r2v: prompt + reference image

    content[] 每个元素:type(text/image_url/video_url/audio_url) + role(可选)
    """
    items: list[dict] = [{"type": "text", "text": args.prompt}]
    if args.image:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.image)}, "role": "first_frame"}
        )
    if args.last_frame:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.last_frame)}, "role": "last_frame"}
        )
    if args.ref_image:
        items.append(
            {"type": "image_url", "image_url": {"url": resolve_image(args.ref_image)}, "role": "reference_image"}
        )
    if args.ref_video:
        items.append(
            {"type": "video_url", "video_url": {"url": resolve_media_url(args.ref_video, "ref-video")}, "role": "reference_video"}
        )
    return items


def mm_video_build_payload(model: str, args: argparse.Namespace) -> dict:
    """构造 MiniMax V2 视频生成请求体。

    通用字段:model / content[] / duration / resolution / ratio
    i2v 场景宽高比由输入图片决定,ratio 恒为 adaptive(官方文档);此处仅在用户显式
    传 --ratio 时带上,否则省略让服务端自判。
    """
    payload: dict = {
        "model": model,
        "content": mm_video_build_content(model, args),
        "duration": args.duration,
        "resolution": args.resolution,
    }
    # t2v 场景 ratio 必填且不能为 adaptive;i2v 由图片决定 ratio 应省略。
    # 此处简化:仅在无 --image 时带 ratio(对齐官方示例的 t2va 必填 ratio 约束)。
    if args.ratio and not args.image:
        payload["ratio"] = args.ratio
    return payload


def mm_video_submit(model: str, args: argparse.Namespace, api_key: str) -> str:
    payload = mm_video_build_payload(model, args)
    resp = post_json(MM_VIDEO_CREATE, payload, mm_headers(api_key), timeout=60)
    # V2 响应:顶层 task_id(V2 不再用 base_resp 信封,错误走 HTTP 状态码)
    task_id = resp.get("task_id") or resp.get("id")
    if not task_id:
        die(
            f"minimax video submit: no task id in response: "
            f"raw={json.dumps(resp, ensure_ascii=False)}"
        )
    return task_id


def mm_video_poll(task_id: str, api_key: str) -> str:
    """轮询 MiniMax V2 视频任务,成功时返回 task.content.url(成片下载地址)。"""
    url = MM_VIDEO_QUERY.format(task_id=task_id)
    deadline = time.time() + MM_TIMEOUT
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        resp = get_json(url, mm_headers(api_key), timeout=30)
        task = resp.get("task") or resp  # V2 响应在 task 字段下,兜底兼容顶层
        status = (task.get("status") or "").lower()
        log(f"minimax video poll #{attempt}: status={status}")
        if status == "succeeded":
            content = task.get("content") or {}
            video_url = content.get("url") or content.get("video_url")
            if not video_url:
                die(f"minimax video succeeded but no content.url: {json.dumps(resp, ensure_ascii=False)}")
            return video_url
        if status in {"failed", "cancelled"}:
            err = task.get("error") or {}
            raise TaskFailed(
                f"minimax video task {status}: code={err.get('code', '')} msg={err.get('message', '')}"
            )
        time.sleep(MM_POLL_INTERVAL)
    die(f"minimax video timed out after {MM_TIMEOUT}s (task {task_id})")


def mm_video_candidates(args: argparse.Namespace) -> list[str]:
    """MiniMax 视频候选链:目前仅 MiniMax-H3。--model 显式指定时只用该模型。"""
    return [MM_VIDEO_MODELS["hailuo-h3"]]


# ---- MiniMax 音乐生成 ---------------------------------------------------------


def mm_music_build_payload(args: argparse.Namespace) -> dict:
    """构造 MiniMax 音乐生成请求体。

    官方字段:model(music-3.0) / prompt(风格描述) / lyrics(歌词,可含 [verse]/[chorus] 标签)
    / audio_setting(sample_rate/bitrate/format)。
    """
    payload: dict = {
        "model": MM_MUSIC_MODEL,
        "prompt": args.prompt,
    }
    lyrics = getattr(args, "lyrics", None)
    if lyrics:
        payload["lyrics"] = lyrics
    audio_setting: dict = {"format": "mp3", "sample_rate": 44100, "bitrate": 256000}
    payload["audio_setting"] = audio_setting
    return payload


def mm_music_generate(args: argparse.Namespace, api_key: str) -> bytes:
    """MiniMax 音乐生成:POST /v1/music_generation,返回音频二进制。

    官方示例为同步 POST,响应体即音频字节流(或 JSON 含 base64 audio 字段)。
    """
    payload = mm_music_build_payload(args)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MM_MUSIC_CREATE, data=data, headers=mm_headers(api_key), method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read()
            if "audio" in content_type or content_type == "application/octet-stream":
                return body
            json_resp = json.loads(body.decode("utf-8"))
            audio_field = json_resp.get("audio") or (json_resp.get("data") or {}).get("audio")
            if audio_field:
                return base64.b64decode(audio_field)
            die(f"minimax music: no audio in response: {json.dumps(json_resp, ensure_ascii=False)}")
    except urllib.error.HTTPError as exc:
        die(f"minimax music HTTP {exc.code}: {exc.read().decode(errors='replace')}")
    except urllib.error.URLError as exc:
        die(f"minimax music URLError: {exc.reason}")


# ---- platform: DashScope ------------------------------------------------------

def ds_build_input(args: argparse.Namespace) -> dict:
    inp: dict = {"prompt": args.prompt}

    media: list[dict] = []
    if args.image:
        media.append({"type": "first_frame", "url": resolve_image(args.image)})
    if args.last_frame:
        media.append({"type": "last_frame", "url": resolve_image(args.last_frame)})
    if args.ref_image:
        m = {"type": "reference_image", "url": resolve_image(args.ref_image)}
        media.append(m)
    if args.ref_video:
        m = {"type": "reference_video", "url": resolve_media_url(args.ref_video, "ref-video")}
        media.append(m)
    if media:
        inp["media"] = media
    return inp


def ds_submit(model: str, args: argparse.Namespace, api_key: str, base: str) -> str:
    payload: dict = {
        "model": model,
        "input": ds_build_input(args),
        "parameters": {
            "resolution": args.resolution.upper(),
            "ratio": args.ratio,
            "duration": args.duration,
            "watermark": False,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    resp = post_json(f"{base}{DS_CREATE_PATH}", payload, headers, timeout=60)
    task_id = (resp.get("output") or {}).get("task_id")
    if not task_id:
        die(f"dashscope submit: no task id in response: {json.dumps(resp, ensure_ascii=False)}")
    return task_id


def ds_poll(task_id: str, api_key: str, base: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{base}{DS_QUERY_PATH.format(task_id=task_id)}"
    deadline = time.time() + DS_TIMEOUT
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        resp = get_json(url, headers, timeout=30)
        out = resp.get("output") or {}
        status = out.get("task_status", "")
        log(f"dashscope poll #{attempt}: status={status}")
        if status == "SUCCEEDED":
            video_url = out.get("video_url")
            if not video_url:
                die(f"dashscope succeeded but no video_url: {json.dumps(resp, ensure_ascii=False)}")
            return video_url
        if status in {"FAILED", "CANCELED", "UNKNOWN"}:
            raise TaskFailed(
                f"dashscope task {status}: {out.get('code', '')} {out.get('message', '')}"
            )
        time.sleep(DS_POLL_INTERVAL)
    die(f"dashscope timed out after {DS_TIMEOUT}s (task {task_id})")


class TaskFailed(Exception):
    pass


# ---- model candidate chains ---------------------------------------------------

def volc_candidates(args: argparse.Namespace) -> list[str]:
    chain = [VOLC_MODELS["fast"], VOLC_MODELS["normal"], VOLC_MODELS["mini"]]
    # fast only supports 720p; skip it for 1080p
    if args.resolution.lower() == "1080p":
        chain = [m for m in chain if m != VOLC_MODELS["fast"]]
    return chain


def ds_candidates(args: argparse.Namespace, mode: str) -> list[str]:
    # Mode-level capability checks (apply to every model in the chain)
    # happyhorse 系列最短 3 秒；wan2.7 托底同链，统一要求 ≥3（脚本规划已遵守）
    if args.duration < 3:
        die("百炼视频生成最短 3 秒；请将 --duration 提到 ≥3 或拆分片段")
    # i2v 仅首帧，不支持首+尾帧
    if mode == "i2v" and args.last_frame:
        die("i2v 不支持首+尾帧（仅首帧）；请去掉 --last-frame")
    # r2v 仅参考图，不支持参考视频、不支持首帧
    if mode == "r2v" and args.ref_video:
        die("r2v 仅支持参考图（--ref-image）；不支持 --ref-video")
    if mode == "r2v" and args.image:
        die(
            "r2v 仅支持参考图（--ref-image）；"
            "不要传 --image 或 --prev-segment（r2v 不收首帧）"
        )
    return list(DS_MODEL_CHAIN[mode])


# ---- orchestration ------------------------------------------------------------

def resolve_platform() -> str:
    has_ds = bool(os.environ.get("MODELSTUDIO_API_KEY", "").strip() or os.environ.get("DASHSCOPE_API_KEY", "").strip())
    has_volc = bool(os.environ.get("AWK_GEN_KEY", "").strip())
    has_mm = bool(os.environ.get("MINIMAX_API_KEY", "").strip())
    if has_ds:
        return "dashscope"
    if has_volc:
        return "volcengine"
    if has_mm:
        return "minimax"
    print(
        "[error] 未检测到任何视频生成平台的环境变量"
        "（MODELSTUDIO_API_KEY / AWK_GEN_KEY / MINIMAX_API_KEY 均未设置）。\n"
        "[hint] 请改用 pexels-footage 和 pixabay-footage 技能搜集素材：\n"
        "       1) pexels-footage 搜索并下载 9:16 竖屏素材（按片段时长设 --min-duration/--max-duration）\n"
        "       2) pexels 无结果时用 pixabay-footage 兜底\n"
        "       3) 下载后按脚本片段编号重命名放入 artifacts/，再用 check.py 自检\n"
        "       若要启用 AI 直生成，请配置 MODELSTUDIO_API_KEY（阿里云百炼，优先）/ "
        "AWK_GEN_KEY（火山引擎）/ MINIMAX_API_KEY（MiniMax Hailuo）。\n"
        "       ⚠️ MINIMAX_API_KEY 缺失时，需提醒用户实时提供，然后交 IT engineer 配置。",
        file=sys.stderr,
    )
    sys.exit(2)


def resolve_mode(args: argparse.Namespace) -> str:
    if args.ref_video or args.ref_image:
        return "r2v"
    if args.image:
        return "i2v"
    return "t2v"


def run_one(platform: str, model: str, args: argparse.Namespace, api_key: str) -> str:
    """Submit + poll for a single model. Returns video URL or raises."""
    if platform == "volcengine":
        task_id = volc_submit(model, args, api_key)
        log(f"volcengine task submitted: {task_id} (model={model})")
        return volc_poll(task_id, api_key)
    if platform == "minimax":
        task_id = mm_video_submit(model, args, api_key)
        log(f"minimax video task submitted: {task_id} (model={model})")
        return mm_video_poll(task_id, api_key)
    base = ds_base_for_model(model)
    task_id = ds_submit(model, args, api_key, base)
    log(f"dashscope task submitted: {task_id} (model={model} base={base})")
    return ds_poll(task_id, api_key, base)


def generate(platform: str, candidates: list[str], args: argparse.Namespace, api_key: str) -> str:
    """Try candidate models in order. HttpError/TaskFailed trigger fallback
    unless the user explicitly pinned --model (then only transient retries)."""
    pinned = args.model is not None
    models = candidates if pinned else candidates
    last_err = ""
    for idx, model in enumerate(models):
        for attempt in range(1, 4):  # up to 3 transient retries per model
            try:
                return run_one(platform, model, args, api_key)
            except TaskFailed as exc:
                last_err = str(exc)
                log(f"model {model} task failed: {last_err}")
                break  # task-level failure → fall back to next model, no retry
            except HttpError as exc:
                last_err = str(exc)
                if exc.code in RETRYABLE_HTTP and attempt < 3:
                    log(f"model {model} HTTP {exc.code}, retrying ({attempt}/2)")
                    time.sleep(3 * attempt)
                    continue
                log(f"model {model} submit error: {last_err}")
                break  # fall back to next model
        if pinned:
            break  # respect explicit user choice — no chain walk
        if idx < len(models) - 1:
            next_model = models[idx + 1]
            log(f"falling back to next model: {next_model}")
            append_decision(f"fallback | {model} → {next_model} | reason: {last_err}")
    append_decision(f"all candidates exhausted | models: {','.join(models)} | last error: {last_err}")
    die(f"all model attempts failed; last error: {last_err}")


def cmd_music(args: argparse.Namespace) -> None:
    """MiniMax 背景音乐生成子命令。

    流程:mm_music_generate(同步 POST /v1/music_generation)→ 写文件。
    仅 minimax 平台支持,需 MINIMAX_API_KEY。
    """
    api_key = (os.environ.get("MINIMAX_API_KEY") or "").strip()
    if not api_key:
        die("MINIMAX_API_KEY 未设置 —— 请实时提醒用户提供 key,然后交 IT engineer 配置")
    output_path = ensure_safe_output(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"minimax music generation: prompt={args.prompt!r}")
    audio_bytes = mm_music_generate(args, api_key)
    output_path.write_bytes(audio_bytes)
    meta = output_path.with_suffix(".json")
    meta.write_text(
        json.dumps(
            {
                "platform": "minimax",
                "capability": "music",
                "model": MM_MUSIC_MODEL,
                "prompt": args.prompt,
                "lyrics": getattr(args, "lyrics", None),
                "file": str(output_path),
                "bytes": len(audio_bytes),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[done] music saved: {output_path}")
    print(f"[done] metadata:    {meta}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Video AIGC generation via Volcengine Seedance, Aliyun DashScope, or MiniMax Hailuo (auto-detected)."
    )
    sub = parser.add_subparsers(dest="command")

    # ── 默认子命令:video(向后兼容,无子命令时走 video) ──
    p_video = sub.add_parser("video", help="视频生成(默认,可省略 video 子命令)")
    p_video.add_argument("--prompt", required=True, help="画面+音频描述（声画同出）")
    p_video.add_argument("--image", default=None, help="首帧图片：URL 或本地路径（→ i2v）")
    p_video.add_argument("--prev-segment", default=None, dest="prev_segment",
                         help="上一段视频本地路径：脚本自动抽取其末帧作为本段首帧（人物故事首尾帧对齐）。与 --image 互斥")
    p_video.add_argument("--last-frame", default=None, dest="last_frame", help="尾帧图片：URL 或本地路径（i2v 首尾帧）")
    p_video.add_argument("--ref-image", default=None, dest="ref_image", help="参考图片：URL 或本地路径（→ r2v，角色/主体一致性）")
    p_video.add_argument("--ref-video", default=None, dest="ref_video", help="参考视频 URL（→ r2v，需公网 URL）")
    p_video.add_argument("--duration", type=int, default=8, help="时长（秒），默认 8")
    p_video.add_argument("--ratio", default="9:16", choices=sorted(VALID_RATIOS), help="宽高比，默认 9:16")
    p_video.add_argument("--resolution", default="720P", choices=["720P", "1080P"], help="分辨率，默认 720P")
    p_video.add_argument("--no-audio", action="store_false", dest="audio", help="关闭声画同出（默认开启）")
    p_video.add_argument("--platform", default=None, choices=["volcengine", "dashscope", "minimax"], help="覆盖平台自动检测")
    p_video.add_argument("--model", default=None, help="指定模型 id（关闭候选链 fallback）")
    p_video.add_argument("--output", required=True, help="输出 MP4 路径（相对工作区，须在 output_videos/tmp/fragments/artifacts 下）")

    # ── music 子命令:minimax 背景音乐生成 ──
    p_music = sub.add_parser("music", help="MiniMax 背景音乐生成(需 MINIMAX_API_KEY)")
    p_music.add_argument("--prompt", required=True, help="音乐描述(风格/情绪/乐器)")
    p_music.add_argument("--duration", type=int, default=None, dest="music_duration", help="音乐时长(秒),不传走模型默认")
    p_music.add_argument("--output", required=True, help="输出音频路径(相对工作区,须在 output_videos/tmp/fragments/artifacts 下)")

    return parser


def cmd_video(args: argparse.Namespace) -> None:
    if args.duration < 2 or args.duration > 15:
        die("--duration 必须在 2–15 秒之间")

    # --prev-segment: extract last frame of the previous segment and use it as
    # the first frame. Enables人物故事模式 A.1 首尾帧对齐: each segment starts
    # from the exact end frame of the previous one.
    prev_segment_frame: Path | None = None
    if args.prev_segment:
        if args.image:
            die("--prev-segment 与 --image 互斥：首帧由上一段末帧决定")
        prev_segment_frame = extract_last_frame(Path(args.prev_segment))
        args.image = str(prev_segment_frame)

    platform = args.platform or resolve_platform()
    mode = resolve_mode(args)

    if platform == "volcengine":
        api_key = (os.environ.get("AWK_GEN_KEY") or "").strip()
        if not api_key:
            die("AWK_GEN_KEY 未设置")
        candidates = [args.model] if args.model else volc_candidates(args)
    elif platform == "minimax":
        api_key = (os.environ.get("MINIMAX_API_KEY") or "").strip()
        if not api_key:
            die("MINIMAX_API_KEY 未设置 —— 请实时提醒用户提供 key,然后交 IT engineer 配置")
        candidates = [args.model] if args.model else mm_video_candidates(args)
    else:
        api_key = (os.environ.get("MODELSTUDIO_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or "").strip()
        if not api_key:
            die("MODELSTUDIO_API_KEY / DASHSCOPE_API_KEY 未设置")
        candidates = [args.model] if args.model else ds_candidates(args, mode)

    output_path = ensure_safe_output(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log(
        f"platform={platform} mode={mode} candidates={candidates} "
        f"duration={args.duration}s ratio={args.ratio} resolution={args.resolution} audio={args.audio}"
    )
    video_url = generate(platform, candidates, args, api_key)
    download(video_url, output_path)

    meta = output_path.with_suffix(".json")
    meta.write_text(
        json.dumps(
            {
                "platform": platform,
                "mode": mode,
                "model_candidates": candidates,
                "duration": args.duration,
                "ratio": args.ratio,
                "resolution": args.resolution,
                "audio": args.audio,
                "video_url": video_url,
                "file": str(output_path),
                "prev_segment": args.prev_segment,
                "first_frame_from_prev": str(prev_segment_frame) if prev_segment_frame else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[done] video saved: {output_path}")
    print(f"[done] metadata:    {meta}")


def main() -> None:
    parser = build_parser()

    # 向后兼容:无子命令时,把全部 argv 当成 video 子命令的参数
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["video"] + argv

    # video 子命令可省略:如果第一个 token 不是已知子命令,默认走 video
    known_subcommands = {"video", "music"}
    if argv and argv[0] not in known_subcommands:
        argv = ["video"] + argv

    args = parser.parse_args(argv)

    if args.command == "music":
        cmd_music(args)
    else:
        cmd_video(args)


if __name__ == "__main__":
    main()
