/**
 * relay-sign.ts — client 侧调用 relay sign 服务的统一入口（TS）
 *
 * 产品拆分后签名收敛到 relay（D1）。本模块供 viral-chaser / xhs-content-ops / published-track 等
 * TS skill 共用。RELAY_BASE_URL + OFB_KEY 由 entrypoint 从 daemon.env 注入。
 *
 * 接口对应 relay 仓 services/sign/：
 *   POST /api/v1/sign/xhs/headers  → 仅签名
 *   POST /api/v1/sign/xhs/proxy    → 签名 + 代请求 edith，返回平台原始 JSON
 *   POST /api/v1/sign/douyin        → 算 a_bogus
 * todo: 这里还缺一个bilibili签名接口，后续需要加上
 */

const RELAY_BASE_URL =
  process.env.RELAY_BASE_URL ?? "http://localhost:3020";
const OFB_KEY = process.env.OFB_KEY;

function assertOfbKey(): string {
  if (!OFB_KEY) {
    throw new Error(
      "OFB_KEY 未配置：签名需走 relay，请设置 OFB_KEY 环境变量（见 daemon.env）",
    );
  }
  return OFB_KEY;
}

interface RelayEnvelope<T> {
  success: boolean;
  data: T | null;
  error: string | null;
  meta?: Record<string, unknown>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const key = assertOfbKey();
  const resp = await fetch(`${RELAY_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-OFB-Key": key,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });
  const env = (await resp.json()) as RelayEnvelope<T>;
  if (!resp.ok || !env.success) {
    throw new Error(`relay ${path} 失败 (${resp.status}): ${env.error ?? resp.statusText}`);
  }
  return env.data as T;
}

// ── xhs ─────────────────────────────────────────────────────────────────────

export interface XhsSignInput {
  uri: string;
  method?: "get" | "post";
  payload?: Record<string, unknown>;
  params?: Record<string, unknown>;
  cookies: Record<string, string>;
  signFormat?: string;
  xRap?: boolean;
}

export interface XhsProxyInput extends XhsSignInput {
  xsecToken?: string;
  xsecSource?: string;
}

/** 仅签名，返回完整 headers（含 Cookie / UA / 签名头），client 自行发请求 */
export async function xhsHeaders(input: XhsSignInput): Promise<Record<string, string>> {
  const data = await postJson<{ headers: Record<string, string> }>(
    "/api/v1/sign/xhs/headers",
    {
      uri: input.uri,
      method: input.method ?? "post",
      payload: input.payload ?? {},
      params: input.params ?? {},
      cookies: input.cookies,
      sign_format: input.signFormat ?? "xys",
      x_rap: Boolean(input.xRap),
    },
  );
  return data.headers;
}

/** 签名 + 代请求 edith，返回平台原始 JSON（client 自行 parse） */
export async function xhsProxy<T = unknown>(input: XhsProxyInput): Promise<T> {
  return postJson<T>("/api/v1/sign/xhs/proxy", {
    uri: input.uri,
    method: input.method ?? "post",
    payload: input.payload ?? {},
    params: input.params ?? {},
    cookies: input.cookies,
    xsec_token: input.xsecToken,
    xsec_source: input.xsecSource,
    sign_format: input.signFormat ?? "xys",
    x_rap: Boolean(input.xRap),
  });
}

// ── douyin ──────────────────────────────────────────────────────────────────

export interface DouyinSignInput {
  queryString: string;
  postData?: string;
  ua?: string;
}

/** 算 a_bogus（relay 子进程隔离 vendor），client 自行拼 URL 发请求 */
export async function douyinSign(input: DouyinSignInput): Promise<string> {
  const data = await postJson<{ a_bogus: string }>("/api/v1/sign/douyin", {
    queryString: input.queryString,
    postData: input.postData ?? "",
    ua: input.ua,
  });
  return data.a_bogus;
}

export { RELAY_BASE_URL };
