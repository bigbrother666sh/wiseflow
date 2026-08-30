import { z } from "zod";
export { z };

export const AwadaConfigSchema = z
  .object({
    enabled: z.boolean().optional(),
    /** Relay gateway base URL, e.g. "https://relay.example.com". Bot talks HTTP/WS to relay, never Redis directly.
     *  Defaults to the official relay domain (https://relay.openclaw-for-business.com) when unset. */
    relayBaseUrl: z.string().optional(),
    /** Awada key issued by relay admin; carries awada:lane:<laneId> scopes. Sent as X-Awada-Key header.
     *  Distinct from the sign-service OFB_KEY — relay admin issues the two separately. */
    awadaKey: z.string().optional(),
    /** Lane to subscribe to. Maps to awada:events:inbound:<lane>. Optional — when omitted, the server
     *  defaults to the "User" lane. */
    lane: z.string().optional(),
    /** DM policy: open (anyone), pairing (requires approval), or allowlist */
    dmPolicy: z.enum(["open", "pairing", "allowlist"]).optional(),
    /** Allowed user_id_external values for allowlist/pairing */
    allowFrom: z.array(z.string()).optional(),
    /**
     * Max characters per outbound message. When set, long replies are automatically
     * split into multiple messages each no longer than this value.
     * Useful for platforms like WeChat that enforce per-message length limits.
     */
    perMsgMaxLen: z.number().int().positive().optional(),
  })
  .strict();

/** Per-account override (currently unused — awada uses a single default account) */
export const AwadaAccountConfigSchema = z
  .object({
    enabled: z.boolean().optional(),
    name: z.string().optional(),
  })
  .strict();
