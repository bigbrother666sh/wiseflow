/** Unix socket server for the camoufox-cli daemon. */

import * as net from "node:net";
import * as fs from "node:fs";
import { BrowserManager } from "./browser.js";
import { execute } from "./commands.js";
import { parseCommand, serializeResponse, errorResponse, okResponse } from "./protocol.js";
import { getSocketPath, getPidPath } from "./cli.js";

// Idle self-exit is OFF by default (timeout 0). Interactive flows — QR logins,
// human-in-the-loop skills (login-manager, wx-mp/xhs/twitter engagement, ...) —
// routinely wait on the user for minutes, and the old 60s hard ceiling killed
// daemons mid-flow, leaving follow-up commands talking to a fresh about:blank
// page. The backstop against browser-process accumulation is now the
// concurrent daemon cap in cli.ts (MAX_CONCURRENT_DAEMONS, evicts the oldest
// daemon); skills must still `close` when done. Callers can opt back in to
// idle self-exit with --timeout <secs>.

export class DaemonServer {
  private session: string;
  private headless: boolean;
  private timeout: number;
  private socketPath: string;
  private pidPath: string;
  private manager: BrowserManager;
  private server: net.Server | null = null;
  private lastActivity = Date.now();
  private watchdogTimer: ReturnType<typeof setInterval> | null = null;
  // Fail-first queue: a session runs one command at a time. A command that
  // arrives while another is mid-flight fails immediately with guidance text
  // (no hidden queueing/waiting) — see spec §1.1. `close` bypasses this so a
  // stuck session can always be torn down.
  private busy = false;
  // Active client connections. Tracked so `close` can force-destroy them and
  // the server's 'close' event fires promptly even when an in-flight command
  // is hung on something that doesn't react to browser teardown — notably
  // `wait <ms>`, whose `page.waitForTimeout` is a standalone setTimeout that
  // neither rejects on context close nor releases the event loop. Without this,
  // `wait 999999999` + `close` leaves the daemon lingering (socket/pid leak).
  private activeConnections = new Set<net.Socket>();
  // When true (daemon entry point), shutdown() ends with process.exit(0) so a
  // stray timer from an interrupted command can't keep the detached daemon
  // alive. In-process tests pass false and let the event loop drain naturally.
  private forceExit: boolean;

  constructor(opts: { session?: string; headless?: boolean; timeout?: number; persistent?: string | null; proxy?: string | null; geoip?: boolean; locale?: string | null; viewport?: [number, number] | null; forceExit?: boolean }) {
    this.session = opts.session ?? "default";
    this.headless = opts.headless ?? true;
    // 0 disables the idle watchdog: the daemon lives until `close`, SIGTERM,
    // or eviction by the concurrent daemon cap. No hard ceiling — callers who
    // opt in with --timeout get exactly what they asked for.
    this.timeout = Math.max(0, Math.floor(opts.timeout ?? 0));
    this.socketPath = getSocketPath(this.session);
    this.pidPath = getPidPath(this.session);
    this.manager = new BrowserManager(opts.persistent ?? null, opts.proxy ?? null, opts.geoip ?? true, opts.locale ?? null, opts.viewport ?? null);
    this.forceExit = opts.forceExit ?? false;
  }

  async start(): Promise<void> {
    this.cleanupStale();
    this.writePid();
    // Idle timeout watchdog (only when the caller opted in with --timeout > 0)
    if (this.timeout > 0) {
      this.watchdogTimer = setInterval(() => {
        // A command mid-flight (e.g. `wait 90`, a slow `open`) is NOT idle —
        // don't kill the daemon out from under it. Only self-exit when truly
        // idle: no command running AND no activity for the timeout window.
        if (this.busy) return;
        if (Date.now() - this.lastActivity > this.timeout * 1000) {
          process.stderr.write(`[camoufox-cli] Idle timeout (${this.timeout}s), shutting down\n`);
          this.server?.close();
        }
      }, 10000);
    }

    // Signal handlers
    process.on("SIGTERM", () => { this.server?.close(); });
    process.on("SIGINT", () => { this.server?.close(); });

    this.server = net.createServer({ allowHalfOpen: true }, (conn) => this.handleConnection(conn));

    await new Promise<void>((resolve, reject) => {
      this.server!.listen(this.socketPath, () => resolve());
      this.server!.on("error", reject);
    });

    process.stderr.write(`[camoufox-cli] Daemon listening session=${this.session}\n`);

    // Wait until server closes
    await new Promise<void>((resolve) => {
      this.server!.on("close", resolve);
    });

    await this.shutdown();
  }

  private handleConnection(conn: net.Socket): void {
    this.activeConnections.add(conn);
    conn.on("close", () => { this.activeConnections.delete(conn); });
    conn.on("error", () => { this.activeConnections.delete(conn); });

    let data = "";
    let handled = false;

    const processData = async () => {
      if (handled) return;
      const nlIdx = data.indexOf("\n");
      if (nlIdx < 0) return;
      handled = true;

      this.lastActivity = Date.now();
      const line = data.slice(0, nlIdx).trim();
      if (!line) { conn.destroy(); return; }

      let command: { id?: string; action?: string; params?: Record<string, unknown> };
      try {
        command = parseCommand(line);
      } catch (e: any) {
        conn.end(Buffer.from(JSON.stringify({ id: "?", success: false, error: String(e) }) + "\n"));
        return;
      }

      const action = command.action ?? "";
      const cmdId = (command.id as string) || "?";

      // `info` returns daemon metadata (session + headless mode). It bypasses
      // the fail-first busy gate so the CLI can probe a running daemon's mode
      // before deciding whether to reuse or restart it (see ensureDaemon in
      // cli.ts — headless is fixed at spawn, so a mode switch requires a respawn).
      if (action === "info") {
        conn.end(serializeResponse(okResponse(cmdId, { session: this.session, headless: this.headless })));
        return;
      }

      // `close` is the recovery escape hatch — always allowed, even while a
      // previous command is mid-flight (it tears the daemon down anyway).
      if (action !== "close" && this.busy) {
        conn.end(serializeResponse(
          errorResponse(cmdId, `session ${this.session} 正忙，请等待当前操作完成后再试`),
        ));
        return;
      }

      this.busy = true;
      try {
        if (action === "open") {
          (command.params as Record<string, unknown>).headless ??= this.headless;
        }

        const response = await execute(this.manager, command as any);
        conn.end(serializeResponse(response));

        if (action === "close") {
          // Stop accepting new connections, then force-destroy every OTHER
          // active connection so the server's 'close' event fires even if a
          // prior command is stuck on a timer that won't release (e.g. wait
          // <ms>). This connection is left alone — conn.end() above already
          // half-closes it after flushing the response to the client.
          this.server?.close();
          for (const c of this.activeConnections) {
            if (c === conn) continue;
            try { c.destroy(); } catch {}
          }
        }
      } catch (e: any) {
        conn.end(Buffer.from(JSON.stringify({ id: cmdId, success: false, error: String(e) }) + "\n"));
      } finally {
        this.busy = false;
      }
    };

    conn.on("data", (chunk) => {
      data += chunk.toString();
      processData();
    });

    conn.on("end", () => { processData(); });
  }

  private cleanupStale(): void {
    if (fs.existsSync(this.socketPath)) {
      if (fs.existsSync(this.pidPath)) {
        try {
          const pid = parseInt(fs.readFileSync(this.pidPath, "utf-8").trim(), 10);
          process.kill(pid, 0); // Check if alive
          process.stderr.write(`[camoufox-cli] Daemon already running (pid ${pid})\n`);
          process.exit(1);
        } catch {
          // Stale pid, clean up
        }
      }
      fs.unlinkSync(this.socketPath);
    }
  }

  private writePid(): void {
    fs.writeFileSync(this.pidPath, String(process.pid));
  }

  private async shutdown(): Promise<void> {
    if (this.watchdogTimer) clearInterval(this.watchdogTimer);
    // Give manager.close() (Playwright context.close -> kills camoufox-bin) a hard
    // 8s budget. Under memory pressure or heavy-JS pages (xhs/twitter), Firefox can
    // hang on context.close() and the await never resolves - the daemon zombifies,
    // camoufox-bin never exits, and processes accumulate until the 13GB box OOMs.
    // This is the idle-self-exit twin of the killDaemon fix (commit 0773afb): same
    // context.close() hang race, but the idle-watchdog shutdown path was missed
    // (2026-07-27 死机: 12:36 heartbeat 的 3 个 camoufox-bin idle 自退时卡死没退，
    // 40 分钟内存不回落，叠加 13:17 小贝 xhs 任务撑爆). 8s matches killDaemon's
    // budget (Firefox close routinely takes 2-5s). On timeout, SIGKILL the whole
    // process group so camoufox-bin is reaped.
    let timedOut = false;
    await Promise.race([
      this.manager.close(),
      new Promise<void>((resolve) => setTimeout(() => { timedOut = true; resolve(); }, 8000)),
    ]);
    if (timedOut) {
      process.stderr.write(`[camoufox-cli] manager.close() timed out after 8s (context.close hung); force-killing process group to reap camoufox-bin\n`);
      // Unlink socket/pid first (sync, before the kill takes us down) so the next
      // ensureDaemon doesn't see a stale socket. Then SIGKILL the whole process
      // group: daemon.js is spawned detached:true (own pgid leader), and
      // camoufox-bin + content procs are its children - killing only this pid
      // would orphan camoufox-bin holding the profile lock + RAM (see 0773afb).
      for (const p of [this.socketPath, this.pidPath]) { try { fs.unlinkSync(p); } catch {} }
      if (this.forceExit) {
        // SIGTERM first (graceful): Firefox catches it, flushes GPU fences/
        // WebRender state, exits cleanly. Direct SIGKILL on WebRender-active
        // Firefox dangles amdgpu fences → hard-lock (2026-08-01 Vega freeze,
        // memory 48). Wait 3s, then SIGKILL the whole group as last resort.
        try { process.kill(-process.pid, "SIGTERM"); } catch {}
        await new Promise((r) => setTimeout(r, 3000));
        try { process.kill(-process.pid, "SIGKILL"); } catch {}
        process.exit(1);
      }
    }
    if (this.server) {
      try { this.server.close(); } catch {}
    }
    for (const c of this.activeConnections) {
      try { c.destroy(); } catch {}
    }
    for (const p of [this.socketPath, this.pidPath]) {
      try { fs.unlinkSync(p); } catch {}
    }
    // A command interrupted mid-flight (e.g. wait <ms>) may have left a
    // standalone setTimeout keeping the event loop alive. The detached daemon
    // must exit deterministically so its socket/pid are reclaimed.
    if (this.forceExit) process.exit(0);
  }
}
