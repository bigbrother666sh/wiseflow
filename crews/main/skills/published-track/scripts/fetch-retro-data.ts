#!/usr/bin/env -S node --experimental-strip-types
/**
 * fetch-retro-data.ts — 复盘数据抓取（第一层：纯 HTTP + cookie + 签名）
 *
 * 这是复盘数据抓取的第一层，只拿基础互动指标（播放/点赞/评论数）。
 * 第二层（完播率/转粉率/评论内容等深度数据）通过 browser tool + evaluate
 * CDP 拦截实现，不在此脚本中。
 *
 * 签名方案复用：
 *   - 抖音: a_bogus（复用 viral-chaser 的 vendor/douyin.js）
 *   - B站:  WBI 签名（复用 viral-chaser 逻辑）
 *   - 快手:  GraphQL（无需签名）
 *
 * Cookie 来源: login-manager（~/.openclaw/logins/{platform}.json）
 *   小红书使用 xhs-browse cookie（消费者端域 www.xiaohongshu.com）
 *
 * Usage:
 *   node fetch-retro-data.ts --platform douyin --content-id <aweme_id>
 *   node fetch-retro-data.ts --platform bilibili --content-id <bvid>
 *   node fetch-retro-data.ts --platform kuaishou --content-id <photo_id>
 *   node fetch-retro-data.ts --platform xhs --content-id <note_id>
 *
 * Exit codes:
 *   0  成功 — JSON 输出到 stdout
 *   1  一般错误
 *   2  Cookie 无效/未登录 → 调用方应触发 login-manager
 */

import { readFileSync, existsSync } from "fs"
import { join } from "path"
import { homedir } from "os"
import { execFile, execFileSync } from "child_process"
import { promisify } from "util"
import {
  xhsBrowserHeaders,
  extractInitialState,
  fetchXhsNoteFromHtml,
  XhsCaptchaError,
  XhsNoteInaccessibleError,
} from "../../_shared/xhs-html-note.ts"

const execFileAsync = promisify(execFile)

// ─── Types ────────────────────────────────────────────────────────────────

interface CookieRecord { name: string; value: string; domain?: string }

interface SessionData {
  platform: string
  /** camoufox-cli 原生格式：cookies 是对象数组；向后兼容旧字符串格式 */
  cookies?: CookieRecord[] | string
  /** 旧字段保留兼容；新格式下 UA 走独立 .ua.json 文件 */
  user_agent?: string
  updated_at?: string
}

interface RetroResult {
  ok: boolean
  platform: string
  contentId: string
  stats: Record<string, number>
  comments: Array<{ cid: string; text: string; likeCount: number; userName: string }>
  error?: string
  msg?: string
}

// ─── Session ──────────────────────────────────────────────────────────────

const SESSIONS_DIR = join(homedir(), ".openclaw", "logins")
const DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

function readSession(platform: string): SessionData | null {
  const path = join(SESSIONS_DIR, `${platform}.json`)
  if (!existsSync(path)) return null
  try {
    const raw = JSON.parse(readFileSync(path, "utf-8"))
    // camoufox-cli `cookies export` 写的是裸数组（见 patches/camoufox-cli/src/commands.ts
    // `writeFileSync(path, JSON.stringify(cookies))`），消费方统一归一化为 {cookies: [...]}，
    // 否则 requireSession 的 `!data.cookies` 判空会把有效 cookie 误报 SESSION_EXPIRED。
    if (Array.isArray(raw)) return { platform, cookies: raw } as SessionData
    return raw as SessionData
  } catch {
    return null
  }
}

function readUserAgent(platform: string): string {
  const path = join(SESSIONS_DIR, `${platform}.ua.json`)
  if (!existsSync(path)) return DEFAULT_UA
  try {
    const data = JSON.parse(readFileSync(path, "utf-8")) as { userAgent?: string }
    return data.userAgent || DEFAULT_UA
  } catch {
    return DEFAULT_UA
  }
}

function requireSession(platform: string): SessionData {
  const data = readSession(platform)
  const empty = !data || !data.cookies || (Array.isArray(data.cookies) && data.cookies.length === 0)
  if (empty) {
    process.stderr.write(JSON.stringify({ ok: false, error: "SESSION_EXPIRED", platform }) + "\n")
    process.exit(2)
  }
  return data
}

function parseCookies(raw: CookieRecord[] | string | undefined): Record<string, string> {
  const dict: Record<string, string> = {}
  if (Array.isArray(raw)) {
    for (const c of raw) {
      if (c && typeof c.name === "string" && typeof c.value === "string") {
        dict[c.name] = c.value
      }
    }
  } else if (typeof raw === "string" && raw) {
    for (const item of raw.split(";")) {
      const trimmed = item.trim()
      if (!trimmed || !trimmed.includes("=")) continue
      const [k, ...rest] = trimmed.split("=")
      dict[k.trim()] = rest.join("=").trim()
    }
  }
  return dict
}

function cookieHeader(dict: Record<string, string>): string {
  return Object.entries(dict).map(([k, v]) => `${k}=${v}`).join("; ")
}

/** 从 session + 独立 UA 文件拿 UA（spec §4 原则 4，同时导入 cookie + UA） */
function sessionUA(platform: string, session: SessionData): string {
  return readUserAgent(platform) || session.user_agent || DEFAULT_UA
}

// ─── 抖音 ──────────────────────────────────────────────────────────────────

async function fetchDouyin(awemeId: string): Promise<RetroResult> {
  const session = requireSession("douyin")
  const cookieDict = parseCookies(session.cookies)
  const ua = sessionUA("douyin", session)
  const cookieStr = cookieHeader(cookieDict)

  // 签名 + COMMON_PARAMS + webid/msToken/verifyFp 走 _shared/douyin-web.ts。
  // 早期此处只发 aweme_id+msToken+a_bogus，缺 COMMON_PARAMS，抖音 Janus 网关回 200 空体，
  // 长期取不到数（静默 __no_metrics__）。复用 viral-chaser 同款请求形态后修复。
  const { douyinWebGet } = await import("../../_shared/douyin-web.ts")

  const result: RetroResult = {
    ok: true,
    platform: "douyin",
    contentId: awemeId,
    stats: {},
    comments: [],
  }

  // 视频详情（aweme/detail 接口）——只取数，不碰评论
  // （参考 wiseflow4-pro douyin aweme_processor.__call__ → get_video_by_id →
  //  update_douyin_aweme：读 statistics 的 digg_count/collect_count/comment_count/share_count。）
  console.error("  → 调抖音 API 获取视频详情...")
  try {
    const { status, data } = await douyinWebGet<any>(
      "/aweme/v1/web/aweme/detail/",
      { aweme_id: awemeId },
      cookieStr,
      ua,
    )
    const aweme = data?.aweme_detail
    if (aweme) {
      const stats = aweme.statistics || {}
      result.stats = {
        playCount: stats.play_count || 0,
        likeCount: stats.digg_count || 0,
        commentCount: stats.comment_count || 0,
        shareCount: stats.share_count || 0,
        collectCount: stats.collect_count || 0,
      }
      console.error(`  ✓ 播放 ${result.stats.playCount} / 点赞 ${result.stats.likeCount} / 评论 ${result.stats.commentCount}`)
    } else {
      console.error(`  ⚠️ 视频详情接口返回 ${status} 但无 aweme_detail（cookie 可能失效）`)
    }
  } catch (e) {
    console.error(`  ⚠️ 视频详情获取失败: ${e}`)
  }

  return result
}

// ─── B站 ───────────────────────────────────────────────────────────────────

const BILI_API = "https://api.bilibili.com"
const BILI_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

async function fetchBilibili(bvid: string): Promise<RetroResult> {
  const result: RetroResult = {
    ok: true,
    platform: "bilibili",
    contentId: bvid,
    stats: {},
    comments: [],
  }

  // 视频详情（公开 API，无需 cookie）——只取数，不碰评论
  // （参考 wiseflow4-pro bilibili video_processor.get_video_detail：读 View.stat 的
  //  like/view/danmaku/reply/coin/favorite/share。此处用更轻的 /view 公开端点，字段同。）
  console.error("  → 调 B站 API 获取视频详情...")
  try {
    const resp = await fetch(`${BILI_API}/x/web-interface/view?bvid=${bvid}`, {
      headers: { "User-Agent": BILI_UA },
      signal: AbortSignal.timeout(15_000),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json() as any
    if (data.code !== 0) throw new Error(data.message)

    const stat = data.data.stat
    result.stats = {
      viewCount: stat.view || 0,
      likeCount: stat.like || 0,
      coinCount: stat.coin || 0,
      favoriteCount: stat.favorite || 0,
      shareCount: stat.share || 0,
      danmakuCount: stat.danmaku || 0,
      replyCount: stat.reply || 0,
    }
    console.error(`  ✓ 播放 ${result.stats.viewCount} / 点赞 ${result.stats.likeCount} / 评论 ${result.stats.replyCount}`)
  } catch (e) {
    console.error(`  ⚠️ B站数据获取失败: ${e}`)
  }

  return result
}

// ─── 快手 ──────────────────────────────────────────────────────────────────

const KUAISHOU_GQL = "https://www.kuaishou.com/graphql"

async function fetchKuaishou(photoId: string): Promise<RetroResult> {
  const session = requireSession("kuaishou")
  const cookieDict = parseCookies(session.cookies)
  const ua = sessionUA("kuaishou", session)

  const result: RetroResult = {
    ok: true,
    platform: "kuaishou",
    contentId: photoId,
    stats: {},
    comments: [],
  }

  // 视频详情（GraphQL）——只取数，不碰评论（参考 wiseflow4-pro kuaishou video_processor.get_video_detail）
  // likeCount 是展示数，realLikeCount 才是真实点赞数（参考 update_kuaishou_video 读 realLikeCount）。
  console.error("  → 调快手 GraphQL 获取视频详情...")
  try {
    const query = `query visionVideoDetail($photoId: String) { visionVideoDetail(photoId: $photoId) { photo { id viewCount realLikeCount commentCount } } }`
    const resp = await fetch(KUAISHOU_GQL, {
      method: "POST",
      headers: {
        "User-Agent": ua,
        "Cookie": cookieHeader(cookieDict),
        "Content-Type": "application/json",
        "Referer": "https://www.kuaishou.com/",
        "Origin": "https://www.kuaishou.com",
      },
      body: JSON.stringify({ query, variables: { photoId } }),
      signal: AbortSignal.timeout(15_000),
    })
    if (resp.ok) {
      const data = await resp.json() as any
      const photo = data?.data?.visionVideoDetail?.photo
      if (photo) {
        result.stats = {
          viewCount: photo.viewCount || 0,
          likeCount: photo.realLikeCount || 0,
          commentCount: photo.commentCount || 0,
        }
        console.error(`  ✓ 播放 ${result.stats.viewCount} / 点赞 ${result.stats.likeCount}`)
      }
    }
  } catch (e) {
    console.error(`  ⚠️ 快手详情获取失败: ${e}`)
  }

  return result
}

// ─── 小红书 ────────────────────────────────────────────────────────────────
//
// 走 get_note_by_id_from_html 路线（借鉴 MediaCrawlerPro-Python xhs/client.py）：
// 直接 GET 笔记详情网页 https://www.xiaohongshu.com/explore/{note_id}?xsec_token=...，
// 解析 window.__INITIAL_STATE__.note.noteDetailMap[note_id].note.interactInfo 拿互动计数。
//
// 为何不走 feed API（/api/sns/web/v1/feed）：feed 接口需 xsec_token 且极易触发滑块验证
// （MediaCrawlerPro get_note_by_id 原注释：「开启xsec_token详情接口特别容易出现滑块验证」，
// 实测 500）。HTML 路线只需 cookie + 浏览器头，无需 relay 签名，风控远低于 feed。
//
// headers 形态参考 MediaCrawlerPro xhs/client.py 的 headers 属性（accept-language /
// cache-control / pragma / priority / referer / sec-ch-ua* / sec-fetch-* / ua / cookie）。
// 因是真实页面导航（非 XHR），sec-fetch 用 document/navigate 而非 cors/empty，
// accept 用 text/html —— 比 MediaCrawlerPro 复用 API 头更贴合真实浏览器，camoufox 造的
// cookie 本就来自页面导航，保持一致降低风控。
//
// xhsBrowserHeaders / extractInitialState / fetchXhsNoteFromHtml / parseXhsCount 复用
// _shared/xhs-html-note.ts（与 viral-chaser / xhs-content-ops 同源，避免三处重复解析逻辑）。

/** profile 页 SSR 解析出的单条笔记（2026-07-25 起 xhs 把 SSR 里的 note id 置空，
 * id 可能为空串——此时靠 title 匹配拿 xsec_token）。 */
interface XhsProfileEntry {
  id: string
  title: string
  xsecToken: string
  xsecSource: string
}

/** 解析 profile 页 window.__INITIAL_STATE__.user.notes，解 Vue ref 后取笔记条目列表。
 * 纯 HTTP：GET /user/profile/{user_id}（带 cookie）即可，无需 camoufox。返回 null 表示抓取/解析失败。
 *
 * 2026-07-25 起 xhs 改版：SSR 里每条笔记的 id/noteCard.noteId 全部置空（客户端 hydration 才回填），
 * 但 xsecToken 和 noteCard.displayTitle 仍在。故不再只按 id 建映射，而是返回完整条目列表，
 * 由调用方先按 id 匹配（兼容旧结构/未来回滚），miss 再按 title 匹配。 */
async function fetchXhsProfileEntries(
  userId: string,
  cookieStr: string,
  ua: string,
): Promise<XhsProfileEntry[] | null> {
  const url = `https://www.xiaohongshu.com/user/profile/${userId}`
  try {
    const resp = await fetch(url, {
      headers: xhsBrowserHeaders(ua, cookieStr),
      signal: AbortSignal.timeout(20_000),
    })
    if (!resp.ok) return null
    const html = await resp.text()
    if (/website-login\/captcha/.test(html)) return null
    const state = extractInitialState(html)
    if (!state) return null
    const unref = (v: any): any => (v && v.__v_isRef && v._rawValue !== undefined ? v._rawValue : v)
    const notes = unref(state?.user?.notes)
    const entries: XhsProfileEntry[] = []
    if (Array.isArray(notes)) {
      for (const grp of notes) {
        const g = unref(grp)
        if (!Array.isArray(g)) continue
        for (const n of g) {
          const nn = unref(n)
          const card = nn?.noteCard ?? {}
          const token = nn?.xsecToken || card?.xsecToken
          if (!token) continue
          entries.push({
            id: String(nn?.id || card?.noteId || ""),
            title: String(card?.displayTitle ?? nn?.displayTitle ?? ""),
            xsecToken: String(token),
            xsecSource: nn?.xsecSource || card?.xsecSource || "pc_feed",
          })
        }
      }
    }
    return entries
  } catch {
    return null
  }
}

/** 标题归一化：去首尾空白、折叠空白、去尾部省略号（SSR displayTitle 可能截断）。 */
function normalizeXhsTitle(s: string): string {
  return s.replace(/[\s　]+/g, " ").trim().replace(/[.…]+$/, "")
}

/** 按标题在 profile 条目里找唯一匹配：精确相等优先，其次前缀互含（防截断，最短 6 字符起）。
 * 多条歧义时返回 null（宁可失败也不错配）。 */
function matchXhsEntryByTitle(entries: XhsProfileEntry[], title: string): XhsProfileEntry | null {
  const target = normalizeXhsTitle(title)
  if (!target) return null
  const exact = entries.filter(e => normalizeXhsTitle(e.title) === target)
  if (exact.length === 1) return exact[0]
  if (exact.length > 1) return null
  const prefix = entries.filter(e => {
    const t = normalizeXhsTitle(e.title)
    if (t.length < 6 || target.length < 6) return false
    return t.startsWith(target) || target.startsWith(t)
  })
  return prefix.length === 1 ? prefix[0] : null
}

/** 取 xhs-browse 自身 user_id：优先读 xhs-user-id.cache，缺失则调 get-xhs-user-id.sh（relay sign + user/me）。 */
function readXhsUserId(): string {
  const root = join(import.meta.dirname, "../../..")
  const skillDir = join(root, "skills", "published-track")
  const cache = join(skillDir, "xhs-user-id.cache")
  if (existsSync(cache)) {
    const v = readFileSync(cache, "utf-8").trim()
    if (/^[0-9a-f]{20,}$/.test(v)) return v
  }
  try {
    const out = execFileSync("bash", [join(skillDir, "scripts", "get-xhs-user-id.sh")], {
      encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"], timeout: 30_000,
    }).trim()
    if (/^[0-9a-f]{20,}$/.test(out)) return out
  } catch { /* get-xhs-user-id.sh 失败，返回空交上游报错 */ }
  return ""
}

async function fetchXhs(noteId: string, xsecToken: string = "", xsecSource: string = "", title: string = ""): Promise<RetroResult> {
  const session = requireSession("xhs-browse")
  const cookieDict = parseCookies(session.cookies)
  const ua = sessionUA("xhs-browse", session)

  if (!cookieDict.a1 || !cookieDict.web_session) {
    process.stderr.write("[fetch-retro-data] 小红书 cookie 缺少 a1 或 web_session\n")
    process.exit(2)
  }

  const result: RetroResult = {
    ok: true,
    platform: "xhs",
    contentId: noteId,
    stats: {},
    comments: [],
  }

  const cookieStr = cookieHeader(cookieDict)

  // 1. 无 xsec_token 时，从自己 profile 页（纯 HTTP）取 note_id→xsec_token 映射。
  //    feed/HTML 路线都强制要 xsec_token；publish_url 不带 token、发布响应也不返 token，
  //    唯一来源是 profile 页 note 列表（每条 note 附 xsecToken）。纯 HTTP，不开 camoufox。
  let token = xsecToken
  let source = xsecSource
  if (!token) {
    console.error("  → 无 xsec_token，从自己 profile 页取映射（纯 HTTP）...")
    const userId = readXhsUserId()
    if (!userId) {
      return { ...result, ok: false, error: "NO_USER_ID", msg: "未取到 self user_id（xhs-user-id.cache 缺失且 get-xhs-user-id.sh 失败）" }
    }
    const entries = await fetchXhsProfileEntries(userId, cookieStr, ua)
    if (!entries) {
      return { ...result, ok: false, error: "PROFILE_FETCH_FAILED", msg: "profile 页抓取/解析失败（可能触发风控/登录态失效）" }
    }
    if (entries.length === 0) {
      // 与"笔记不在列表里"区分开：0 条通常是 SSR 结构再次变化或页面异常，不是笔记问题
      return { ...result, ok: false, error: "PROFILE_MAPPING_EMPTY", msg: "profile 页解析到 0 条笔记条目（SSR 结构可能再次变化，或页面异常/风控），请人工核查解析逻辑" }
    }
    // 先按 id 匹配（旧 SSR 结构/未来回滚仍可用），miss 再按 title 匹配
    // （2026-07-25 起 SSR note id 置空，title 是唯一可用的匹配键）
    let entry = entries.find(e => e.id === noteId) ?? null
    let matchedBy = "id"
    if (!entry && title) {
      entry = matchXhsEntryByTitle(entries, title)
      matchedBy = "title"
    }
    if (!entry) {
      const idsEmpty = entries.every(e => !e.id)
      return {
        ...result, ok: false, error: "NOTE_NOT_IN_PROFILE",
        msg: `profile 首页未匹配到该笔记（共 ${entries.length} 条条目${idsEmpty ? "，SSR note id 全为空" : ""}${title ? "，title 匹配也未命中" : "，未提供 --title 无法按标题匹配"}；可能已删除/私密/超出首页范围）`,
      }
    }
    token = entry.xsecToken
    source = entry.xsecSource || "pc_feed"
    console.error(`  ✓ 映射命中（共 ${entries.length} 条，按 ${matchedBy} 匹配），拿到 xsec_token`)
  }

  // 2. GET 笔记详情页 HTML，解析 interactInfo（复用 _shared/xhs-html-note.ts）
  console.error(`  → GET 小红书笔记详情页 HTML（get_note_by_id_from_html 路线）...`)
  try {
    const note = await fetchXhsNoteFromHtml(noteId, {
      xsecToken: token,
      xsecSource: source,
      cookieStr,
      ua,
    })
    // 解析成功即返回——新发笔记可能四项全 0，属正常态。
    result.stats = {
      likeCount: note.stats.likeCount,
      collectCount: note.stats.collectCount,
      commentCount: note.stats.commentCount,
      shareCount: note.stats.shareCount,
    }
    console.error(`  ✓ 点赞 ${result.stats.likeCount} / 收藏 ${result.stats.collectCount} / 评论 ${result.stats.commentCount} / 分享 ${result.stats.shareCount}`)
    return result
  } catch (e) {
    if (e instanceof XhsCaptchaError) {
      return { ...result, ok: false, error: "NEED_VERIFY", msg: "小红书出现安全验证滑块，请扫码验证后重试" }
    }
    if (e instanceof XhsNoteInaccessibleError) {
      // 评论内容（top_comment）需 comment/page API，同样依赖 xsec_token 且易触发风控；
      // 当前 DB 不存 xsec_token，该 API 本就拿不到，故暂不调。互动计数（含 commentCount）
      // 已从 HTML 拿到，published-track 指标完整。top_comment 待发布侧落 xsec_token 后再补。
      return { ...result, ok: false, error: "NOTE_INACCESSIBLE", msg: "多次重试仍未拿到笔记 interactInfo（可能笔记已删除/私密或触发风控）" }
    }
    return { ...result, ok: false, error: "NOTE_INACCESSIBLE", msg: String(e) }
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = process.argv.slice(2)
  let platform = ""
  let contentId = ""
  let xsecToken = ""
  let xsecSource = ""
  let title = ""

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--platform" && args[i + 1]) platform = args[++i]
    else if (args[i] === "--content-id" && args[i + 1]) contentId = args[++i]
    else if (args[i] === "--xsec-token" && args[i + 1]) xsecToken = args[++i]
    else if (args[i] === "--xsec-source" && args[i + 1]) xsecSource = args[++i]
    else if (args[i] === "--title" && args[i + 1]) title = args[++i]
  }

  if (!platform || !contentId) {
    process.stderr.write("用法: node fetch-retro-data.ts --platform <douyin|bilibili|kuaishou|xhs> --content-id <id> [--xsec-token <t> --xsec-source <s>] [--title <t>]\n")
    process.exit(1)
  }

  let result: RetroResult

  switch (platform) {
    case "douyin":
      result = await fetchDouyin(contentId)
      break
    case "bilibili":
      result = await fetchBilibili(contentId)
      break
    case "kuaishou":
      result = await fetchKuaishou(contentId)
      break
    case "xhs":
      result = await fetchXhs(contentId, xsecToken, xsecSource, title)
      break
    default:
      process.stderr.write(`❌ 不支持的平台: ${platform}\n`)
      process.exit(1)
  }

  process.stdout.write(JSON.stringify(result, null, 2) + "\n")
}

main().catch(e => {
  process.stderr.write(`❌ ${e}\n`)
  process.exit(1)
})
