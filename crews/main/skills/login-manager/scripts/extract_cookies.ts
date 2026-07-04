#!/usr/bin/env -S node --experimental-strip-types
/**
 * extract_cookies.ts — Extract cookies from browser via CDP WebSocket
 *
 * Usage:
 *   extract_cookies.ts <wsUrl> [domainFilter]
 *
 * Arguments:
 *   wsUrl        — CDP WebSocket URL from `browser tabs` response (wsUrl field)
 *   domainFilter — Optional domain filter (e.g., "xiaohongshu.com"). If omitted, returns all cookies.
 *
 * Output: JSON to stdout:
 *   { "ok": true, "cookieCount": N, "cookieString": "name1=val1; name2=val2", "httpOnlyNames": [...] }
 *
 * How to get wsUrl:
 *   1. Run `browser action=tabs` to list all tabs
 *   2. Find the tab with the target platform URL
 *   3. Copy its `wsUrl` field
 *   4. Pass it to this script
 *
 * Why this script exists:
 *   - browser tool has NO direct cookie export action
 *   - document.cookie cannot access httpOnly cookies (e.g., XHS web_session)
 *   - browser act evaluate cannot reach CDP session
 *   - This script connects to CDP WebSocket and calls Network.getAllCookies
 *
 * Requires: Node.js 22+ (uses built-in WebSocket)
 */

const [wsUrl, domainFilter] = process.argv.slice(2)

if (!wsUrl) {
  process.stderr.write(
    "Usage: extract_cookies.ts <wsUrl> [domainFilter]\n" +
    "\n" +
    "  wsUrl        CDP WebSocket URL from browser tabs (wsUrl field)\n" +
    "  domainFilter Optional domain filter (e.g. xiaohongshu.com)\n" +
    "\n" +
    "Example:\n" +
    "  extract_cookies.ts ws://127.0.0.1:18800/devtools/page/ABC123 xiaohongshu.com\n"
  )
  process.exit(1)
}

interface CdpCookie {
  name: string
  value: string
  domain: string
  path: string
  expires: number
  size: number
  httpOnly: boolean
  secure: boolean
  sameSite: string
  priority: string
  sameParty: boolean
  sourceScheme: string
  sourcePort: number
  partitionKey?: string
}

interface CdpResponse {
  id: number
  result?: { cookies: CdpCookie[] }
  error?: { message: string }
}

let msgId = 0

function cdpRequest(method: string, params?: Record<string, unknown>): string {
  return JSON.stringify({ id: ++msgId, method, params: params ?? {} })
}

async function extractCookies(): Promise<void> {
  const ws = new WebSocket(wsUrl)

  const result = await new Promise<CdpCookie[]>((resolve, reject) => {
    const timeout = setTimeout(() => {
      ws.close()
      reject(new Error("CDP WebSocket timeout (10s)"))
    }, 10_000)

    ws.addEventListener("open", () => {
      ws.send(cdpRequest("Network.enable"))
      ws.send(cdpRequest("Network.getAllCookies"))
    })

    ws.addEventListener("message", (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as CdpResponse
        if (msg.id === 2 && msg.result?.cookies) {
          clearTimeout(timeout)
          ws.close()
          resolve(msg.result.cookies)
        }
        if (msg.id === 2 && msg.error) {
          clearTimeout(timeout)
          ws.close()
          reject(new Error(`CDP error: ${msg.error.message}`))
        }
      } catch {
        // Ignore non-response messages (events)
      }
    })

    ws.addEventListener("error", () => {
      clearTimeout(timeout)
      reject(new Error("WebSocket error"))
    })

    ws.addEventListener("close", () => {
      clearTimeout(timeout)
    })
  })

  // Filter by domain if specified
  const filtered = domainFilter
    ? result.filter(c => c.domain.includes(domainFilter))
    : result

  // Build cookie string
  const cookieString = filtered.map(c => `${c.name}=${c.value}`).join("; ")

  process.stdout.write(JSON.stringify({
    ok: true,
    cookieCount: filtered.length,
    cookieString,
    httpOnlyNames: filtered.filter(c => c.httpOnly).map(c => c.name),
  }, null, 2) + "\n")
}

extractCookies().catch((err: Error) => {
  process.stdout.write(JSON.stringify({ ok: false, error: err.message }) + "\n")
  process.exit(1)
})
