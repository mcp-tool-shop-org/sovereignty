// Index landing — light polish per spec §5.
// Daemon connection pill + nav links to /audit, /game, /settings.
// Empty-state onboarding when no games exist.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import pkg from "../../package.json" with { type: "json" };
import { EmptyBoxGlyph, EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Pill } from "../components/Pill";
import { useDaemon } from "../hooks/useDaemon";
import { DaemonClient } from "../lib/daemonClient";
import type { GameSummary } from "../types/daemon";
import styles from "./Index.module.css";

// WEB-UI-D-020: resolve version from package.json at compile time so a future
// version bump can't silently desync. Vite supports JSON imports with type
// attribute natively. Mirrors the SOV_VERSION-was-stale lesson from the
// Stage 8-C v2.1 Wave 8 fix on the Python side.
const APP_VERSION = pkg.version;

export default function Index() {
  const { status, config, error } = useDaemon();
  const [games, setGames] = useState<GameSummary[] | null>(null);

  useEffect(() => {
    if (status !== "running" || !config) return;
    const client = new DaemonClient(config);
    let cancelled = false;
    void client
      .games()
      .then((g) => {
        if (!cancelled) setGames(g);
      })
      .catch(() => {
        if (!cancelled) setGames([]);
      });
    return () => {
      cancelled = true;
    };
  }, [status, config]);

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1>Sovereignty</h1>
        <div className={styles.pills}>
          <DaemonStatusPill />
          {config ? <Pill variant="neutral">{config.network}</Pill> : null}
          {config?.readonly ? (
            <Pill
              variant="warn"
              title="Read-only mode — anchor writes disabled. Restart with `sov daemon start` (no --readonly) to enable anchor writes."
            >
              readonly
            </Pill>
          ) : null}
        </div>
      </header>

      {error ? (
        <p className={styles.error} role="alert">
          Error: {error}
        </p>
      ) : null}
      {status === "loading" ? <LoadingSpinner label="Connecting to daemon" /> : null}

      {games !== null && games.length === 0 ? (
        <EmptyState
          glyph={<EmptyBoxGlyph />}
          title="Welcome"
          body={
            <>
              Start your first game with <code>sov play campfire_v1</code> in your terminal, then
              come back here to watch it live.
            </>
          }
          cta={<Link to="/audit">Open Audit Viewer →</Link>}
        />
      ) : null}

      {games && games.length > 0 ? (
        <section className={styles.summary} aria-label="active games summary">
          <h2 className={styles.h2}>
            {games.length} game{games.length === 1 ? "" : "s"}
          </h2>
          <p className={styles.muted}>
            Latest: <code>{games[0].game_id}</code> ({games[0].ruleset}, round{" "}
            {games[0].current_round}/{games[0].max_rounds})
          </p>
        </section>
      ) : null}

      <nav className={styles.nav} aria-label="primary">
        <Link to="/audit" className={styles.navLink}>
          <strong>Audit Viewer</strong>
          <span className={styles.muted}>Verify XRPL-anchored proofs</span>
        </Link>
        <Link to="/game" className={styles.navLink}>
          <strong>Active Game</strong>
          <span className={styles.muted}>Live state of the current game</span>
        </Link>
        <Link to="/settings" className={styles.navLink}>
          <strong>Settings</strong>
          <span className={styles.muted}>Daemon config + network switcher</span>
        </Link>
      </nav>

      <footer className={styles.footer}>
        <span>v{APP_VERSION}</span>
        <span>·</span>
        <span>{config?.network ?? "—"}</span>
      </footer>
    </main>
  );
}

function DaemonStatusPill() {
  const { status } = useDaemon();
  if (status === "running")
    return (
      <Pill variant="success" live>
        running
      </Pill>
    );
  if (status === "error")
    return (
      <Pill variant="error" live>
        error
      </Pill>
    );
  if (status === "stale")
    return (
      <Pill variant="warn" live>
        stale
      </Pill>
    );
  if (status === "loading")
    return (
      <Pill variant="neutral" live>
        loading
      </Pill>
    );
  return (
    <Pill variant="neutral" live>
      stopped
    </Pill>
  );
}
