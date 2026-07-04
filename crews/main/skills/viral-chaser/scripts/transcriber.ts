#!/usr/bin/env -S node --experimental-strip-types
/**
 * transcriber.ts — ASR transcription via SiliconFlow API
 *
 * 实现说明：Node 24 的 fetch + FormData 在部分环境下会抛
 * "location is not defined" 等兼容异常，改用 python requests 子进程
 * 调 SiliconFlow，与 xhs.ts 同一模式（python3 -c 内联脚本）。
 *
 * API: POST https://api.siliconflow.cn/v1/audio/transcriptions
 * model via env: ASR_MODEL (default: FunAudioLLM/SenseVoiceSmall)
 *
 * 注意：SiliconFlow ASR（SenseVoiceSmall / TeleSpeechASR）官方只返回 text、
 * 不返回 segments/时间戳。因此当 API 未返回 segments 时，本模块基于全文按
 * 句切分、按字数比例在已知音频时长上估算分段，并在结果中置 estimated=true。
 * 若上游将来支持时间戳或切换到 whisper 类模型，真实 segments 仍优先采用。
 */

import { existsSync } from "fs"
import { execFile } from "child_process"
import { promisify } from "util"

const execFileAsync = promisify(execFile)

export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface TranscriptResult {
  text: string
  segments: TranscriptSegment[]
  /** true 表示 segments 是按音频时长估算的，非 ASR 真实时间戳。 */
  estimated?: boolean
}

// ── 估算分段（当 ASR 不返回时间戳时）─────────────────────────────────────────

function splitSentences(text: string): string[] {
  if (!text) return []
  const parts = text.split(/[。！？!?\n\r]+/).map(s => s.trim()).filter(Boolean)
  const out: string[] = []
  for (const p of parts) {
    if (p.length <= 40) {
      out.push(p)
      continue
    }
    // 过长段落再按逗号/分号切，并合并过短碎片避免帧时间戳过密
    const subs = p.split(/[，,；;]+/).map(s => s.trim()).filter(Boolean)
    let buf = ""
    for (const s of subs) {
      if (buf && buf.length + s.length > 40) {
        out.push(buf)
        buf = s
      } else {
        buf = buf ? buf + s : s
      }
    }
    if (buf) out.push(buf)
  }
  return out
}

function synthesizeSegments(text: string, durationSeconds: number): TranscriptSegment[] {
  const sentences = splitSentences(text)
  if (!sentences.length || durationSeconds <= 0) return []
  const totalChars = sentences.reduce((a, s) => a + s.length, 0) || 1
  const segs: TranscriptSegment[] = []
  let accChars = 0
  for (const s of sentences) {
    const start = (accChars / totalChars) * durationSeconds
    accChars += s.length
    const end = (accChars / totalChars) * durationSeconds
    segs.push({
      start: Math.round(start * 10) / 10,
      end: Math.round(end * 10) / 10,
      text: s,
    })
  }
  if (segs.length) segs[segs.length - 1].end = durationSeconds
  return segs
}

const PYTHON_SCRIPT = `
import json, os, sys
try:
    import requests
except ImportError as e:
    print(json.dumps({"ok": False, "error": f"requests 不可用: {e}"}))
    sys.exit(1)

audio_path = sys.argv[1]
api_key = os.environ.get("SILICONFLOW_API_KEY")
if not api_key:
    print(json.dumps({"ok": False, "error": "环境变量 SILICONFLOW_API_KEY 未设置"}))
    sys.exit(1)

model = os.environ.get("ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")
url = "https://api.siliconflow.cn/v1/audio/transcriptions"

try:
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        data = {"model": model}
        r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"},
                          files=files, data=data, timeout=180)
except Exception as e:
    print(json.dumps({"ok": False, "error": f"请求失败: {e}"}))
    sys.exit(1)

if not r.ok:
    print(json.dumps({"ok": False, "error": f"ASR API 失败 ({r.status_code}): {r.text[:500]}"}))
    sys.exit(1)

try:
    body = r.json()
except Exception as e:
    print(json.dumps({"ok": False, "error": f"响应解析失败: {e}"}))
    sys.exit(1)

segs = []
for s in (body.get("segments") or []):
    try:
        segs.append({"start": float(s.get("start", 0)), "end": float(s.get("end", 0)), "text": s.get("text", "")})
    except Exception:
        continue

print(json.dumps({"ok": True, "text": body.get("text", ""), "segments": segs}, ensure_ascii=False))
`

export async function transcribeAudio(audioPath: string, durationSeconds = 0): Promise<TranscriptResult> {
  if (!existsSync(audioPath)) {
    throw new Error(`音频文件不存在: ${audioPath}`)
  }

  const { stdout } = await execFileAsync(
    "python3",
    ["-c", PYTHON_SCRIPT, audioPath],
    { timeout: 200_000, maxBuffer: 10 * 1024 * 1024 },
  )

  let data: { ok: boolean; text?: string; segments?: TranscriptSegment[]; error?: string }
  try {
    data = JSON.parse(stdout.trim())
  } catch (e) {
    throw new Error(`ASR 响应解析失败: ${(e as Error).message}; raw=${stdout.slice(0, 500)}`)
  }

  if (!data.ok) {
    throw new Error(data.error || "ASR 未知错误")
  }

  const apiSegments = (data.segments ?? []).map(s => ({
    start: s.start,
    end: s.end,
    text: s.text,
  }))

  // ASR 返回了真实 segments → 直接用
  if (apiSegments.length) {
    return { text: data.text ?? "", segments: apiSegments, estimated: false }
  }

  // 上游未返回时间戳 → 按音频时长估算分段
  const estimatedSegments = synthesizeSegments(data.text ?? "", durationSeconds)
  if (estimatedSegments.length) {
    process.stderr.write(
      `[transcriber] ASR 未返回时间戳，按音频时长估算 ${estimatedSegments.length} 个分段\n`,
    )
  }
  return {
    text: data.text ?? "",
    segments: estimatedSegments,
    estimated: estimatedSegments.length > 0,
  }
}
