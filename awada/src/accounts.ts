import { DEFAULT_ACCOUNT_ID } from "openclaw/plugin-sdk/channel-plugin-common";
import type { ClawdbotConfig } from "openclaw/plugin-sdk";
import type { AwadaConfig, ResolvedAwadaAccount } from "./types.js";

/** Official relay gateway endpoint — used when channels.awada.relayBaseUrl is not set. */
export const DEFAULT_RELAY_BASE_URL = "https://relay.openclaw-for-business.com";

function getAwadaCfg(cfg: ClawdbotConfig): AwadaConfig | undefined {
  return cfg.channels?.awada as AwadaConfig | undefined;
}

export function resolveAwadaAccount(params: {
  cfg: ClawdbotConfig;
  accountId?: string | null;
}): ResolvedAwadaAccount {
  const awadaCfg = getAwadaCfg(params.cfg);
  const accountId = params.accountId?.trim() || DEFAULT_ACCOUNT_ID;
  const enabled = awadaCfg?.enabled !== false;
  // relayBaseUrl defaults to the official relay domain; only awadaKey is truly required.
  // lane is optional — when omitted, the server defaults to the "User" lane.
  const relayBaseUrl = awadaCfg?.relayBaseUrl?.trim() || DEFAULT_RELAY_BASE_URL;
  const awadaKey = awadaCfg?.awadaKey?.trim() || undefined;
  const lane = awadaCfg?.lane?.trim() || "";
  const configured = Boolean(awadaKey);

  return {
    accountId,
    enabled,
    configured,
    relayBaseUrl,
    awadaKey,
    lane,
    config: awadaCfg ?? {},
  };
}

export function listAwadaAccountIds(_cfg: ClawdbotConfig): string[] {
  return [DEFAULT_ACCOUNT_ID];
}

export function resolveDefaultAwadaAccountId(_cfg: ClawdbotConfig): string {
  return DEFAULT_ACCOUNT_ID;
}
