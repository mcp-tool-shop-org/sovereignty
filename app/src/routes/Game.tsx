// /game — passive real-time state display.
// Read-only viewer (gameplay verbs CLI-only per Wave 3 spec §10).
//
// SSE consumption per spec §3:
//   - daemon.ready → pulse to live
//   - daemon.shutdown → pulse to stopped + banner
//   - game.state_changed (active id) → SINGLE re-fetch (handled by useGameState)
//   - anchor.* → append to events log (NO re-fetch)
//   - error → append with error styling

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { EventFeed, type FeedEntry } from "../components/EventFeed";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Pill } from "../components/Pill";
import { PlayerCard } from "../components/PlayerCard";
import { RoundTimeline } from "../components/RoundTimeline";
import { useDaemon } from "../hooks/useDaemon";
import { useDaemonEvents } from "../hooks/useDaemonEvents";
import { useGameState } from "../hooks/useGameState";
import type { SSEEvent } from "../types/daemon";
import styles from "./Game.module.css";

const EVENT_LOG_LIMIT = 20;

export default function Game() {
  const { status, config, error: daemonError } = useDaemon();
  const { activeGameId, state, loading, error: stateError } = useGameState();
  const [events, setEvents] = useState<FeedEntry[]>([]);
  const [pulse, setPulse] = useState<"live" | "stopped">("live");

  const onEvent = useCallback((event: SSEEvent) => {
    if (event.type === "daemon.ready") setPulse("live");
    if (event.type === "daemon.shutdown") setPulse("stopped");
    setEvents((prev) => {
      const next = [...prev, { ts: Date.now(), event }];
      return next.length > EVENT_LOG_LIMIT ? next.slice(-EVENT_LOG_LIMIT) : next;
    });
  }, []);
  useDaemonEvents(onEvent);

  // Reset pulse on daemon up/down.
  useEffect(() => {
    if (status === "running") setPulse("live");
    else if (status === "none") setPulse("stopped");
  }, [status]);

  if (status === "loading" || (loading && !state)) {
    return (
      <main className={styles.main}>
        <Nav />
        <LoadingSpinner label="Loading game state" />
      </main>
    );
  }

  if (status !== "running" || !config) {
    return (
      <main className={styles.main}>
        <Nav />
        <EmptyState title="Daemon not running" body="Start the daemon to view the active game." />
        {daemonError ? (
          <p className={styles.error} role="alert">
            {daemonError}
          </p>
        ) : null}
      </main>
    );
  }

  if (!activeGameId || !state || state.game_over) {
    return (
      <main className={styles.main}>
        <Nav />
        <EmptyState
          title="No active game"
          body={
            <>
              Start one with <code>sov play campfire_v1</code> in your terminal, then come back here
              to watch it live.
            </>
          }
          cta={<Link to="/audit">Open Audit Viewer →</Link>}
        />
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <Nav />

      <header className={styles.header}>
        <h1>Active Game</h1>
        <div className={styles.pills}>
          <Pill variant={pulse === "live" ? "success" : "warn"} live>
            {pulse === "live" ? "● Live" : "● Stopped"}
          </Pill>
          <Pill variant="neutral">daemon ready</Pill>
        </div>
      </header>

      <div className={styles.gameMeta}>
        <code className={styles.gameId}>{activeGameId}</code>
        <span className={styles.muted}>{state.config.ruleset}</span>
        <span>
          Round {state.current_round} of {state.config.max_rounds}
        </span>
        <span>
          {state.players.length} player{state.players.length === 1 ? "" : "s"}
        </span>
      </div>

      {stateError ? (
        <p className={styles.error} role="alert">
          {stateError}
        </p>
      ) : null}

      <section className={styles.players} aria-label="players">
        {state.players.map((player) => (
          <PlayerCard key={player.name} player={player} ruleset={state.config.ruleset} />
        ))}
      </section>

      <section className={styles.section} aria-label="round timeline">
        <h2 className={styles.h2}>Round timeline</h2>
        <RoundTimeline
          total={state.config.max_rounds}
          current={state.current_round}
          gameOver={state.game_over}
        />
      </section>

      <section className={styles.section} aria-label="recent events">
        <h2 className={styles.h2}>Recent events</h2>
        <EventFeed events={events} limit={EVENT_LOG_LIMIT} />
      </section>
    </main>
  );
}

function Nav() {
  return (
    <nav aria-label="primary">
      <Link to="/">Home</Link>
      <Link to="/audit">Audit</Link>
      <Link to="/game" aria-current="page">
        Game
      </Link>
      <Link to="/settings">Settings</Link>
    </nav>
  );
}
