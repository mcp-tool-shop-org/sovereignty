// /settings — daemon config display + network switcher with 3 guardrails.
//
// Per spec §4 guardrails (each must trip BEFORE daemon-restart flow runs):
//   1. started_by_shell == false → refuse + inline message + disable Apply
//   2. Active game has non-empty pending-anchors → refuse + inline + disable Apply
//   3. Switching to/from mainnet (either direction) → <dialog> confirm
//
// Restart flow (when guardrails clear): stop → poll status → start with new args.

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Pill } from "../components/Pill";
import { useDaemon } from "../hooks/useDaemon";
import { DaemonClient } from "../lib/daemonClient";
import { daemonStatus } from "../lib/invoke";
import type { GameSummary, XRPLNetwork } from "../types/daemon";
import styles from "./Settings.module.css";

const NETWORKS: XRPLNetwork[] = ["testnet", "mainnet", "devnet"];

interface ExtendedDaemonStatus {
  state: string;
  /** Whether the Tauri shell started this daemon (vs externally via CLI). */
  started_by_shell?: boolean;
}

export default function Settings() {
  const { status, config, error, stopDaemon, startDaemon } = useDaemon();
  const [busy, setBusy] = useState(false);
  const [targetNetwork, setTargetNetwork] = useState<XRPLNetwork | null>(null);
  const [pendingByGame, setPendingByGame] = useState<Map<string, number>>(new Map());
  const [startedByShell, setStartedByShell] = useState<boolean | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [restartError, setRestartError] = useState<string | null>(null);

  // Derive started_by_shell from extended status (Tauri shell tracks this).
  useEffect(() => {
    if (status !== "running") {
      setStartedByShell(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const s = (await daemonStatus()) as ExtendedDaemonStatus;
        if (!cancelled) {
          // Default to true if shell doesn't report (backward-compat path).
          setStartedByShell(s.started_by_shell ?? true);
        }
      } catch {
        if (!cancelled) setStartedByShell(null);
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

  // Guardrails 1 + 2 — disable Apply.
  const guardrailMessage = externallyStarted
    ? "Daemon was started externally — stop it via `sov daemon stop` and restart from the shell to manage networks here."
    : totalPending > 0
      ? "Pending anchors target the current network. Run `sov anchor` to flush them first, then switch networks."
      : null;

  const canApply =
    !!targetNetwork &&
    !!config &&
    targetNetwork !== config.network &&
    !externallyStarted &&
    totalPending === 0 &&
    !busy;

  // Guardrail 3 — mainnet boundary needs confirm.
  const requiresMainnetConfirm =
    !!config && !!targetNetwork && (config.network === "mainnet" || targetNetwork === "mainnet");

  const performRestart = useCallback(
    async (network: XRPLNetwork) => {
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
        await startDaemon(config.readonly, network);
      } catch (e) {
        setRestartError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [config, stopDaemon, startDaemon],
  );

  const onApplyClick = useCallback(() => {
    if (!targetNetwork || !canApply) return;
    if (requiresMainnetConfirm) {
      setConfirmOpen(true);
    } else {
      void performRestart(targetNetwork);
    }
  }, [targetNetwork, canApply, requiresMainnetConfirm, performRestart]);

  const onConfirmMainnet = useCallback(() => {
    setConfirmOpen(false);
    if (targetNetwork) void performRestart(targetNetwork);
  }, [targetNetwork, performRestart]);

  return (
    <main className={styles.main}>
      <nav aria-label="primary">
        <Link to="/">Home</Link>
        <Link to="/audit">Audit</Link>
        <Link to="/game">Game</Link>
        <Link to="/settings" aria-current="page">
          Settings
        </Link>
      </nav>

      <header className={styles.header}>
        <h1>Settings</h1>
        <Pill variant={status === "running" ? "success" : "warn"} live>
          {status}
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
          </dl>
        ) : (
          <p className={styles.muted}>(no daemon config available)</p>
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
          <button type="button" onClick={onApplyClick} disabled={!canApply} aria-busy={busy}>
            {busy ? "Restarting…" : "Apply (restarts daemon)"}
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
        onCancel={() => setConfirmOpen(false)}
      />
    </main>
  );
}
