// /settings — daemon config display + network/mode switcher with 3 guardrails.
//
// Per spec §4 guardrails (each must trip BEFORE daemon-restart flow runs):
//   1. started_by_shell == false → refuse + inline message + disable Apply
//   2. Active game has non-empty pending-anchors → refuse + inline + disable Apply
//   3. Switching to/from mainnet (either direction) → <dialog> confirm
//
// Restart flow (when guardrails clear): stop → poll status → start with new args.
//
// `started_by_shell` is read directly from the daemon-status payload (no `??`
// fallback). When the field is missing — old Rust shell binary, or a status
// fetch failure — the UI fails CLOSED: treat the daemon as externally-started
// so the user can't accidentally switch networks against the guardrail.

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { EmptyState } from "../components/EmptyState";
import { Pill } from "../components/Pill";
import { useDaemon } from "../hooks/useDaemon";
import type { DaemonUiStatus } from "../hooks/useDaemon";
import { DaemonClient } from "../lib/daemonClient";
import { daemonStatus } from "../lib/invoke";
import type { GameSummary, XRPLNetwork } from "../types/daemon";
import styles from "./Settings.module.css";

/** Title-case display label for the daemon status pill. Maps the raw
 *  DaemonUiStatus tokens (which include the awkward "none") to user-facing
 *  copy. WEB-UI-C-020. */
function statusLabel(status: DaemonUiStatus): string {
  switch (status) {
    case "loading":
      return "Loading";
    case "running":
      return "Running";
    case "stale":
      return "Stale";
    case "error":
      return "Error";
    default:
      return "Stopped";
  }
}

const NETWORKS: XRPLNetwork[] = ["testnet", "mainnet", "devnet"];

/** Cross-platform daemon log location hint. Mac/Linux follow XDG conventions;
 *  Windows uses %LOCALAPPDATA%. Source: docs/v2.1-views.md §4 layout. */
function daemonLogPathHint(): string {
  if (typeof navigator !== "undefined" && /Win/i.test(navigator.platform)) {
    return "%LOCALAPPDATA%\\sov\\daemon.log";
  }
  return "~/.local/state/sov/daemon.log";
}

export default function Settings() {
  const { status, config, error, stopDaemon, startDaemon } = useDaemon();
  const [busy, setBusy] = useState(false);
  const [targetNetwork, setTargetNetwork] = useState<XRPLNetwork | null>(null);
  const [pendingByGame, setPendingByGame] = useState<Map<string, number>>(new Map());
  // null = not yet probed; once probed we have a definite boolean. Field-
  // missing on the wire is normalized to `false` (fail-closed) below.
  const [startedByShell, setStartedByShell] = useState<boolean | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState<"network" | "mode" | null>(null);
  const [restartError, setRestartError] = useState<string | null>(null);

  // Read started_by_shell directly off the daemon-status response. Spec §4
  // pins this as the source of truth for Guardrail #1; no `?? true` fallback
  // — that was the audit finding (WEB-UI-002, dead-code guardrail).
  useEffect(() => {
    if (status !== "running") {
      setStartedByShell(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const s = await daemonStatus();
        if (!cancelled) {
          // Fail closed: an old shell binary that doesn't ship the field
          // (undefined) is treated as externally-started. Stricter, safer.
          setStartedByShell(s.started_by_shell === true);
        }
      } catch {
        if (!cancelled) setStartedByShell(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status]);

  // Probe pending-anchors for each game. Re-runs after restart (busy) so the
  // freshly-restarted daemon's pending state is reflected.
  // biome-ignore lint/correctness/useExhaustiveDependencies: busy is intentional reload trigger
  useEffect(() => {
    if (status !== "running" || !config) return;
    const client = new DaemonClient(config);
    let cancelled = false;
    (async () => {
      try {
        const games: GameSummary[] = await client.games();
        const out = new Map<string, number>();
        for (const g of games) {
          try {
            const pending = await client.pendingAnchors(g.game_id);
            const count = Object.keys(pending).length;
            if (count > 0) out.set(g.game_id, count);
          } catch {
            // ignore — empty implies 0
          }
        }
        if (!cancelled) setPendingByGame(out);
      } catch {
        if (!cancelled) setPendingByGame(new Map());
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status, config, busy]);

  const totalPending = Array.from(pendingByGame.values()).reduce((a, b) => a + b, 0);
  const externallyStarted = startedByShell === false;

  // Guardrails 1 + 2 — disable Apply on either switcher. Copy refresh per
  // WEB-UI-C-008 (lead with situation, name recovery, drop "shell" ambiguity)
  // and WEB-UI-C-009 (name the consequence — orphaned anchors — first).
  const guardrailMessage = externallyStarted
    ? "This daemon was started outside the desktop app. Run `sov daemon stop` to stop it; the desktop app will auto-start a shell-managed daemon on next launch."
    : totalPending > 0
      ? "Switching networks would orphan the pending anchors targeted at the current network. Run `sov anchor` to flush them first."
      : null;

  const canApplyNetwork =
    !!targetNetwork &&
    !!config &&
    targetNetwork !== config.network &&
    !externallyStarted &&
    totalPending === 0 &&
    !busy;

  // Mode switcher — same guardrails 1 + 2 (mainnet confirm doesn't apply since
  // mode toggle doesn't change network).
  const targetReadonly = config ? !config.readonly : false;
  const canApplyMode = !!config && !externallyStarted && totalPending === 0 && !busy;

  // Guardrail 3 — mainnet boundary needs confirm.
  const requiresMainnetConfirm =
    !!config && !!targetNetwork && (config.network === "mainnet" || targetNetwork === "mainnet");

  const performRestart = useCallback(
    async (network: XRPLNetwork, readonly: boolean) => {
      if (!config) return;
      setBusy(true);
      setRestartError(null);
      try {
        await stopDaemon();
        // Poll until state is "none", max 10s.
        const deadline = Date.now() + 10000;
        while (Date.now() < deadline) {
          try {
            const s = await daemonStatus();
            if (s.state === "none") break;
          } catch {
            // Tauri may transiently throw — keep polling.
          }
          await new Promise((r) => setTimeout(r, 250));
        }
        await startDaemon(readonly, network);
      } catch (e) {
        setRestartError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [config, stopDaemon, startDaemon],
  );

  const onApplyNetworkClick = useCallback(() => {
    if (!targetNetwork || !canApplyNetwork || !config) return;
    if (requiresMainnetConfirm) {
      setPendingMode("network");
      setConfirmOpen(true);
    } else {
      void performRestart(targetNetwork, config.readonly);
    }
  }, [targetNetwork, canApplyNetwork, requiresMainnetConfirm, performRestart, config]);

  const onApplyModeClick = useCallback(() => {
    if (!canApplyMode || !config) return;
    void performRestart(config.network, targetReadonly);
  }, [canApplyMode, performRestart, config, targetReadonly]);

  const onConfirmMainnet = useCallback(() => {
    setConfirmOpen(false);
    if (pendingMode === "network" && targetNetwork && config) {
      void performRestart(targetNetwork, config.readonly);
    }
    setPendingMode(null);
  }, [targetNetwork, performRestart, pendingMode, config]);

  // Daemon-down empty state — WEB-UI-C-003. Mirrors the Audit + Game routes:
  // names the recovery command up front so the user is never silently blocked.
  // Loading state passes through (the page chrome renders with the loading
  // pill); only the explicit "not running" cases short-circuit here.
  if (status !== "running" && status !== "loading") {
    return (
      <main className={styles.main}>
        <Nav />
        <EmptyState
          title="Daemon not running"
          body={
            <>
              Run <code>sov daemon start</code> in your terminal to manage daemon configuration
              here.
            </>
          }
        />
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <Nav />

      <header className={styles.header}>
        <h1>Settings</h1>
        <Pill variant={status === "running" ? "success" : "warn"} live>
          {statusLabel(status)}
        </Pill>
      </header>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      <section className={styles.section} aria-label="daemon configuration">
        <h2 className={styles.h2}>Daemon configuration</h2>
        {config ? (
          <dl className={styles.configList}>
            <dt>URL</dt>
            <dd>http://127.0.0.1:{config.port}</dd>
            <dt>Port</dt>
            <dd>{config.port}</dd>
            <dt>Network</dt>
            <dd>
              <Pill variant="accent">{config.network}</Pill>
            </dd>
            <dt>Mode</dt>
            <dd>
              <Pill variant={config.readonly ? "warn" : "neutral"}>
                {config.readonly ? "readonly" : "full"}
              </Pill>
            </dd>
            <dt>Started</dt>
            <dd>
              <code>{config.started_iso}</code>
            </dd>
            <dt>IPC version</dt>
            <dd>{config.ipc_version}</dd>
            <dt>Logs</dt>
            <dd>
              <code>{daemonLogPathHint()}</code>
            </dd>
          </dl>
        ) : (
          <p className={styles.muted}>
            Daemon config unavailable. Run <code>sov daemon status --json</code> to inspect.
          </p>
        )}
      </section>

      <section className={styles.section} aria-label="network switcher">
        <h2 className={styles.h2}>Network switcher</h2>
        <fieldset className={styles.fieldset} disabled={busy || status !== "running"}>
          <legend>Switch XRPL network</legend>
          <label className={styles.label} htmlFor="network-select">
            Target network
          </label>
          <select
            id="network-select"
            className={styles.select}
            value={targetNetwork ?? config?.network ?? "testnet"}
            onChange={(e) => setTargetNetwork(e.target.value as XRPLNetwork)}
          >
            {NETWORKS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={onApplyNetworkClick}
            disabled={!canApplyNetwork}
            aria-busy={busy}
            title="Restarts the daemon to apply the network change."
          >
            {busy ? "Restarting…" : "Switch network"}
          </button>
          {guardrailMessage ? (
            <p className={styles.guardrail} role="alert">
              {guardrailMessage}
            </p>
          ) : null}
          {totalPending > 0 ? (
            <p className={styles.muted}>
              Pending anchors:{" "}
              {Array.from(pendingByGame.entries())
                .map(([gid, n]) => `${gid} (${n})`)
                .join(", ")}
            </p>
          ) : null}
        </fieldset>
      </section>

      <section className={styles.section} aria-label="mode switcher">
        <h2 className={styles.h2}>Mode switcher</h2>
        <fieldset className={styles.fieldset} disabled={busy || status !== "running"}>
          <legend>Daemon mode</legend>
          <p className={styles.muted}>
            Current mode: <strong>{config?.readonly ? "readonly" : "full"}</strong>. Readonly mode
            disables anchor writes; full mode requires a wallet seed in <code>XRPL_SEED</code>.
          </p>
          <button
            type="button"
            onClick={onApplyModeClick}
            disabled={!canApplyMode}
            aria-busy={busy}
          >
            {busy ? "Restarting…" : config?.readonly ? "Switch to full mode" : "Switch to readonly"}
          </button>
        </fieldset>
      </section>

      {restartError ? (
        <p className={styles.error} role="alert">
          {restartError}
        </p>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        title="Mainnet switch"
        body={
          <>
            Mainnet anchors cost real XRP. Confirm switch from{" "}
            <strong>{config?.network ?? "?"}</strong> → <strong>{targetNetwork ?? "?"}</strong>?
          </>
        }
        confirmLabel="Switch network"
        cancelLabel="Cancel"
        variant="warn"
        onConfirm={onConfirmMainnet}
        onCancel={() => {
          setConfirmOpen(false);
          setPendingMode(null);
        }}
      />
    </main>
  );
}

function Nav() {
  return (
    <nav aria-label="primary">
      <Link to="/">Home</Link>
      <Link to="/audit">Audit</Link>
      <Link to="/game">Game</Link>
      <Link to="/settings" aria-current="page">
        Settings
      </Link>
    </nav>
  );
}
