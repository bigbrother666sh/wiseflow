#!/usr/bin/env -S node --experimental-strip-types
/**
 * login_manager.ts — Platform session probe & cookie management CLI
 *
 * Commands:
 *   login-manager check  <platform>   Check if stored cookies are still valid
 *   login-manager read   <platform>   Print stored cookies JSON (for other skills)
 *   login-manager write  <platform>   Write cookies from stdin JSON
 *   login-manager status-all          Check all stored sessions at once
 *
 * Exit codes:
 *   0  Success (cookies are valid / operation succeeded)
 *   1  General error
 *   2  Session expired / not found → caller should trigger browser login
 *
 * Cookie storage: ~/.openclaw/logins/{platform}.json
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "fs"
import { homedir } from "os"
import { join } from "path"

// ── Types ─────────────────────────────────────────────────────────────────

type Platform = "douyin" | "bilibili" | "kuaishou" | "xhs" | "xhs-publish" | "xhs-browse" | "weibo" | "zhihu" | "wechat-channels"

interface SessionData {
  platform: Platform
  cookies: string
  user_agent: string
  updated_at: string // ISO 8601
}

const VALID_PLATFORMS: Platform[] = [
  "douyin", "bilibili", "kuaishou", "xhs", "xhs-publish", "xhs-browse",
  "weibo", "zhihu", "wechat-channels",
]
const LOGINS_DIR = join(homedir(), ".openclaw", "logins")

// ── Helpers ───────────────────────────────────────────────────────────────

function printJson(data: unknown): void {
  process.stdout.write(JSON.stringify(data, null, 2) + "\n")
}

function errExit(msg: string, code = 1): never {
  printJson({ ok: false, error: msg })
  process.exit(code)
}

function authExit(platform: string): never {
  printJson({ ok: false, error: "SESSION_EXPIRED", platform })
  process.exit(2)
}

function sessionPath(platform: Platform): string {
  return join(LOGINS_DIR, `${platform}.json`)
}

function readSession(platform: Platform): SessionData | null {
  const p = sessionPath(platform)
  if (!existsSync(p)) return null
  try {
    return JSON.parse(readFileSync(p, "utf-8")) as SessionData
  } catch {
    return null
  }
}

function writeSession(data: SessionData): void {
  mkdirSync(LOGINS_DIR, { recursive: true })
  writeFileSync(sessionPath(data.platform), JSON.stringify(data, null, 2), "utf-8")
}

function defaultHeaders(cookies: string, userAgent?: string): Record<string, string> {
  return {
    "Cookie": cookies,
    "User-Agent": userAgent ??
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
  }
}

// ── Platform probes ───────────────────────────────────────────────────────

async function probeDouyin(session: SessionData): Promise<boolean> {
  const url = "https://www.douyin.com/aweme/v1/web/query/user/"
  const headers = {
    ...defaultHeaders(session.cookies, session.user_agent),
    "Referer": "https://www.douyin.com/",
  }
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    return body.status_code === 0
  } catch {
    return false
  }
}

async function probeBilibili(session: SessionData): Promise<boolean> {
  const url = "https://api.bilibili.com/x/web-interface/nav"
  const headers = defaultHeaders(session.cookies, session.user_agent)
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    if (body.code !== 0) return false
    const data = body.data as Record<string, unknown> | undefined
    return Boolean(data?.isLogin)
  } catch {
    return false
  }
}

async function probeKuaishou(session: SessionData): Promise<boolean> {
  const url = "https://www.kuaishou.com/graphql"
  const query = `query visionProfileUserList($pcursor: String, $ftype: Int) {
  visionProfileUserList(pcursor: $pcursor, ftype: $ftype) {
    result
    fols {
      user_name
      headurl
      user_text
      isFollowing
      user_id
      __typename
    }
    hostName
    pcursor
    __typename
  }
}`
  const postBody = JSON.stringify({
    operationName: "visionProfileUserList",
    variables: { ftype: 1 },
    query,
  })
  const headers = {
    ...defaultHeaders(session.cookies, session.user_agent),
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.kuaishou.com",
    "Referer": "https://www.kuaishou.com/",
  }
  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: postBody,
      signal: AbortSignal.timeout(10_000),
    })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    const data = body.data as Record<string, unknown> | undefined
    const list = data?.visionProfileUserList as Record<string, unknown> | undefined
    return list?.result === 1
  } catch {
    return false
  }
}

async function probeXHS(session: SessionData): Promise<boolean> {
  // 小红书探活：使用页面内容探活而非 API 端点
  // edith.xiaohongshu.com API 需要 X-S/X-B 签名，纯 HTTP fetch 必然 406，
  // 导致 !res.ok → return false → 误判 SESSION_EXPIRED。
  // 改用搜索页 HTML 探活：检查是否出现登录墙标记。
  const cookies = session.cookies
  if (!cookies.includes("a1=") || !cookies.includes("web_session=")) {
    return false
  }
  const url = "https://www.xiaohongshu.com/search_result/?keyword=test&source=web_explore_feed&type=51"
  const headers = {
    ...defaultHeaders(cookies, session.user_agent),
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
  }
  try {
    const res = await fetch(url, { headers, redirect: "manual", signal: AbortSignal.timeout(10_000) })
    // 302/301 到登录页 = 失效
    if (res.status >= 300 && res.status < 400) return false
    if (!res.ok) return false
    const text = await res.text()
    // 页面包含登录墙标记 = 失效
    if (text.includes("passport.xiaohongshu.com") || text.includes('"needLogin":true')) return false
    return true
  } catch {
    // 网络错误但 cookie 格式正确，best-effort 视为有效
    return true
  }
}

async function probeXhsPublish(session: SessionData): Promise<boolean> {
  // 小红书创作者平台（发布用）— 探活 creator.xiaohongshu.com
  const cookies = session.cookies
  if (!cookies.includes("a1=") || !cookies.includes("web_session=")) {
    return false
  }
  // 必须有创作者域 cookie
  if (!cookies.includes("access-token-creator.xiaohongshu.com") &&
      !cookies.includes("galaxy_creator_session_id")) {
    return false
  }
  const url = "https://creator.xiaohongshu.com/publish/publish?source=official"
  const headers = {
    ...defaultHeaders(cookies, session.user_agent),
    "Origin": "https://creator.xiaohongshu.com",
    "Referer": "https://creator.xiaohongshu.com/",
  }
  try {
    const res = await fetch(url, { headers, redirect: "manual", signal: AbortSignal.timeout(10_000) })
    // 302/301 到登录页 = 失效；200 = 有效
    if (res.status >= 300 && res.status < 400) return false
    if (!res.ok) return false
    const text = await res.text()
    // 页面包含登录相关标记 = 失效
    if (text.includes("passport.xiaohongshu.com") || text.includes('"needLogin":true')) return false
    return true
  } catch {
    // 网络错误但 cookie 格式正确，best-effort 视为有效
    return true
  }
}

async function probeXhsBrowse(session: SessionData): Promise<boolean> {
  // 小红书浏览/搜索/互动 — 探活 www.xiaohongshu.com
  const cookies = session.cookies
  if (!cookies.includes("a1=") || !cookies.includes("web_session=")) {
    return false
  }
  const url = "https://www.xiaohongshu.com/search_result/?keyword=%E4%BB%80%E4%B9%88%E8%B5%9B%E9%81%93%E5%8F%AF%E4%BB%A5%E4%B8%80%E8%BE%B9%E5%B8%A6%E5%A8%83%E5%84%BF%E4%B8%80%E8%BE%B9%E5%B9%B2&source=web_explore_feed&type=51"
  const headers = {
    ...defaultHeaders(cookies, session.user_agent),
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
  }
  try {
    const res = await fetch(url, { headers, redirect: "manual", signal: AbortSignal.timeout(10_000) })
    if (res.status >= 300 && res.status < 400) return false
    if (!res.ok) return false
    const text = await res.text()
    // 页面包含登录墙 = 失效
    if (text.includes("passport.xiaohongshu.com") || text.includes('"needLogin":true')) return false
    return true
  } catch {
    return true
  }
}

async function probeWeibo(session: SessionData): Promise<boolean> {
  // Weibo: probe via /ajax/profile/info endpoint
  // Returns user info if logged in, error if not
  const url = "https://weibo.com/ajax/profile/info"
  const headers = {
    ...defaultHeaders(session.cookies, session.user_agent),
    "Referer": "https://weibo.com/",
  }
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    // ok: 1 means logged in, data contains user object
    return body.ok === 1 && Boolean(body.data)
  } catch {
    return false
  }
}

async function probeZhihu(session: SessionData): Promise<boolean> {
  // Zhihu: probe via /api/v4/me (current user info)
  const url = "https://www.zhihu.com/api/v4/me"
  const headers = {
    ...defaultHeaders(session.cookies, session.user_agent),
    "Referer": "https://www.zhihu.com/",
  }
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    // If we get an id field, we're logged in
    return Boolean(body.id)
  } catch {
    return false
  }
}

async function probeWechatChannels(session: SessionData): Promise<boolean> {
  // WeChat Channels: probe via /cgi-bin/mmfinderassistant-bin/auth/auth_data
  // This is a best-effort check — the creator center uses complex auth
  // Check if key cookies exist
  const cookies = session.cookies
  if (!cookies.includes("finder_user") && !cookies.includes("wxuin")) {
    return false
  }
  // Lightweight check: try the creator center home API
  const url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/auth/auth_data"
  const headers = {
    ...defaultHeaders(cookies, session.user_agent),
    "Referer": "https://channels.weixin.qq.com/",
  }
  try {
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return false
    const body = await res.json() as Record<string, unknown>
    // If we get auth data back, session is valid
    return body.ret === 0 || Boolean(body.data)
  } catch {
    // Network error — assume valid if cookies exist (best-effort)
    return true
  }
}

const PROBES: Record<Platform, (s: SessionData) => Promise<boolean>> = {
  douyin: probeDouyin,
  bilibili: probeBilibili,
  kuaishou: probeKuaishou,
  xhs: probeXHS,
  "xhs-publish": probeXhsPublish,
  "xhs-browse": probeXhsBrowse,
  weibo: probeWeibo,
  zhihu: probeZhihu,
  "wechat-channels": probeWechatChannels,
}

// ── Commands ──────────────────────────────────────────────────────────────

async function cmdCheck(platform: Platform): Promise<void> {
  const session = readSession(platform)
  if (!session || !session.cookies) {
    process.stderr.write(`[login-manager] ${platform}: session 文件不存在或为空\n`)
    authExit(platform)
  }

  process.stderr.write(`[login-manager] ${platform}: 正在探活...\n`)
  const ok = await PROBES[platform](session)
  if (!ok) {
    process.stderr.write(`[login-manager] ${platform}: cookie 已失效\n`)
    authExit(platform)
  }

  process.stderr.write(`[login-manager] ${platform}: cookie 有效\n`)
  printJson({ ok: true, platform, cookies: session.cookies, user_agent: session.user_agent })
}

function cmdRead(platform: Platform): void {
  const session = readSession(platform)
  if (!session || !session.cookies) {
    authExit(platform)
  }
  printJson({ ok: true, ...session })
}

function cmdWrite(platform: Platform): void {
  let input = ""
  try {
    input = readFileSync("/dev/stdin", "utf-8")
  } catch {
    errExit("无法读取 stdin")
  }

  let data: { cookies?: string; user_agent?: string }
  try {
    data = JSON.parse(input)
  } catch {
    errExit("stdin 不是有效的 JSON")
  }

  if (!data.cookies) {
    errExit("JSON 中缺少 cookies 字段")
  }

  const session: SessionData = {
    platform,
    cookies: data.cookies,
    user_agent: data.user_agent ??
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    updated_at: new Date().toISOString(),
  }

  writeSession(session)
  process.stderr.write(`[login-manager] ${platform}: session 已保存到 ${sessionPath(platform)}\n`)
  printJson({ ok: true, path: sessionPath(platform) })
}

async function cmdStatusAll(): Promise<void> {
  // Check all platforms that have stored sessions
  if (!existsSync(LOGINS_DIR)) {
    printJson({ ok: true, platforms: [], summary: "no sessions stored" })
    return
  }

  const files = readdirSync(LOGINS_DIR)
    .filter(f => f.endsWith(".json"))
    .map(f => f.replace(".json", "") as Platform)
    .filter(p => VALID_PLATFORMS.includes(p))

  if (files.length === 0) {
    printJson({ ok: true, platforms: [], summary: "no sessions stored" })
    return
  }

  const results: Array<{ platform: string; status: "valid" | "expired" | "error"; updated_at?: string }> = []

  for (const platform of files) {
    const session = readSession(platform)
    if (!session || !session.cookies) {
      results.push({ platform, status: "expired" })
      continue
    }
    try {
      const ok = await PROBES[platform](session)
      results.push({
        platform,
        status: ok ? "valid" : "expired",
        updated_at: session.updated_at,
      })
    } catch {
      results.push({ platform, status: "error" })
    }
  }

  const valid = results.filter(r => r.status === "valid").length
  const expired = results.filter(r => r.status === "expired").length

  process.stderr.write(
    `\n[login-manager] 登录态总览：${valid} 有效 / ${expired} 过期 / ${results.length} 总计\n\n`
  )
  for (const r of results) {
    const icon = r.status === "valid" ? "✅" : r.status === "expired" ? "❌" : "⚠️"
    const time = r.updated_at ? ` (更新于 ${r.updated_at.slice(0, 19)})` : ""
    process.stderr.write(`  ${icon} ${r.platform}${time}\n`)
  }
  process.stderr.write("\n")

  printJson({
    ok: true,
    summary: `${valid} valid / ${expired} expired / ${results.length} total`,
    platforms: results,
  })
}

// ── Main ──────────────────────────────────────────────────────────────────

function main(): void {
  const [command, platformArg] = process.argv.slice(2)

  if (!command || command === "--help") {
    process.stderr.write(
      "Usage:\n" +
      "  login-manager check  <platform>   — probe if cookies are valid\n" +
      "  login-manager read   <platform>   — print stored session JSON\n" +
      "  login-manager write  <platform>   — save session from stdin JSON\n" +
      "  login-manager status-all          — check all stored sessions\n" +
      "\n" +
      "Platforms: douyin, bilibili, kuaishou, xhs, xhs-publish, xhs-browse, weibo, zhihu, wechat-channels\n" +
      "Exit code 2 = session expired / not found\n"
    )
    process.exit(1)
  }

  // status-all doesn't need a platform arg
  if (command === "status-all") {
    cmdStatusAll().catch(e => errExit(String(e)))
    return
  }

  if (!platformArg || !VALID_PLATFORMS.includes(platformArg as Platform)) {
    errExit(`无效的平台: ${platformArg ?? "(空)"}。支持: ${VALID_PLATFORMS.join(", ")}`)
  }
  const platform = platformArg as Platform

  switch (command) {
    case "check":
      cmdCheck(platform).catch(e => errExit(String(e)))
      break
    case "read":
      cmdRead(platform)
      break
    case "write":
      cmdWrite(platform)
      break
    default:
      errExit(`未知命令: ${command}。支持: check, read, write, status-all`)
  }
}

main()
