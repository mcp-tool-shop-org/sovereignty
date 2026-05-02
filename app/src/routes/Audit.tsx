// /audit — XRPL anchor verification viewer (Wave 5 differentiator).
//
// Per spec §2:
//   - Top-level: <details> per game, sorted by latest first.
//   - Expanded: rounds table with anchor status + verify button.
//   - Verify-all-rounds: sequential per-round, cancelable, session-cached.
//   - SSE: payload-driven for anchor events (no re-fetch); single re-fetch
//     for game.state_changed if expanded.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { EventFeed, type FeedEntry } from "../components/EventFeed";
import { ExpandableRow } from "../components/ExpandableRow";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Pill } from "../components/Pill";
import { useDaemon } from "../hooks/useDaemon";
import { useDaemonEvents } from "../hooks/useDaemonEvents";
import { type RoundVerifyState, useVerifyFlow } from "../hooks/useVerifyFlow";
import { DaemonClient } from "../lib/daemonClient";
import { isSafeExplorerUrl } from "../lib/url";
import { anchorStatusDisplay, verifyFailureDisplay } from "../lib/verifyDisplay";
import type { AnchorStatusResponse, GameSummary, SSEEvent } from "../types/daemon";
import styles from "./Audit.module.css";

interface RoundRow {
  round: string;
  status: AnchorStatusResponse;
  // Explorer URL is NOT part of AnchorStatusResponse — daemon's
  // /anchor-status/{round} endpoint never emits it. SSE
  // `anchor.batch_complete` payload carries `explorer_url`; we store it on
  // the row when the event arrives. Stage 7-B WEB-UI-B-003.
  explorerUrl?: string;
}

interface GameSection {
  summary: GameSummary;
  rounds: RoundRow[] | null;
  loading: boolean;
}

export default function Audit() {
  const { status, config, error: daemonError } = useDaemon();
  const [games, setGames] = useState<GameSection[] | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [eventsForGame, setEventsForGame] = useState<Map<string, FeedEntry[]>>(new Map());
  const clientRef = useRef<DaemonClient | null>(null);

  if (config) {
    clientRef.current = new DaemonClient(config);
  } else {
    clientRef.current = null;
  }

  // Initial load.
  const loadGames = useCallback(async () => {
    const client = clientRef.current;
    if (!client) return;
    try {
      const list = await client.games();
      const sorted = [...list].sort((a, b) =>
        b.last_modified_iso.localeCompare(a.last_modified_iso),
      );
      setGames(sorted.map((g) => ({ summary: g, rounds: null, loading: false })));
    } catch {
      setGames([]);
    }
  }, []);

  useEffect(() => {
    if (status !== "running" || !config) return;
    void loadGames();
  }, [status, config, loadGames]);

  // Expand → fetch rounds + statuses for the game.
  const onToggleGame = useCallback(async (gameId: string, open: boolean) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (open) next.add(gameId);
      else next.delete(gameId);
      return next;
    });
    if (!open) return;
    const client = clientRef.current;
    if (!client) return;
    setGames(
      (prev) =>
        prev?.map((g) => (g.summary.game_id === gameId ? { ...g, loading: true } : g)) ?? null,
    );
    try {
      // proofs() returns ProofMeta[] — extract `round` for the URL path-param
      // and the row key. Coerce to string defensively: daemon emits int-or-str
      // per `data.get("round")` from the proof envelope, where round is an int
      // for normal rounds and the string "FINAL" for the closing round.
      const proofs = await client.proofs(gameId);
      const rounds: RoundRow[] = [];
      for (const meta of proofs) {
        const round = String(meta.round);
        try {
          const status = await client.anchorStatus(gameId, round);
          rounds.push({ round, status });
        } catch {
          rounds.push({
            round,
            status: {
              round,
              anchor_status: "missing",
              envelope_hash: meta.envelope_hash ?? null,
            },
          });
        }
      }
      setGames(
        (prev) =>
          prev?.map((g) => (g.summary.game_id === gameId ? { ...g, rounds, loading: false } : g)) ??
          null,
      );
    } catch {
      setGames(
        (prev) =>
          prev?.map((g) =>
            g.summary.game_id === gameId ? { ...g, rounds: [], loading: false } : g,
          ) ?? null,
      );
    }
  }, []);

  // SSE handler — payload-driven flips for anchor events; single re-fetch for state_changed if expanded.
  const onEvent = useCallback(
    (event: SSEEvent) => {
      const data = event.data as Record<string, unknown> | undefined;
      const gid = (data?.game_id as string | undefined) ?? null;

      if (event.type === "anchor.batch_complete" && gid) {
        const txid = data?.txid as string | undefined;
        const explorerUrl = data?.explorer_url as string | undefined;
        const rounds = (data?.rounds as string[] | undefined) ?? [];
        // Flip pending → anchored from payload alone, no re-fetch. Explorer
        // URL rides on RoundRow.explorerUrl (not on AnchorStatusResponse —
        // daemon's anchor-status endpoint never emits it; cross-domain C).
        setGames(
          (prev) =>
            prev?.map((g) => {
              if (g.summary.game_id !== gid) return g;
              if (!g.rounds) return g;
              const updated = g.rounds.map((r) =>
                rounds.includes(r.round)
                  ? {
                      ...r,
                      status: {
                        ...r.status,
                        anchor_status: "anchored" as const,
                        txid,
                      },
                      explorerUrl,
                    }
                  : r,
              );
              return { ...g, rounds: updated };
            }) ?? null,
        );
      }

      if (event.type === "anchor.pending_added" && gid) {
        // Update pending count summary by appending a placeholder row if needed.
        const round = data?.round as string | undefined;
        if (round) {
          setGames(
            (prev) =>
              prev?.map((g) => {
                if (g.summary.game_id !== gid) return g;
                if (!g.rounds) return g;
                const exists = g.rounds.some((r) => r.round === round);
                if (exists) return g;
                return {
                  ...g,
                  rounds: [
                    ...g.rounds,
                    {
                      round,
                      status: {
                        round,
                        anchor_status: "pending",
                        envelope_hash: null,
                      },
                    },
                  ],
                };
              }) ?? null,
          );
        }
      }

      if (event.type === "game.state_changed" && gid && expanded.has(gid)) {
        // Single re-fetch only for expanded game.
        void onToggleGame(gid, true);
      }

      if (gid) {
        setEventsForGame((prev) => {
          const next = new Map(prev);
          const existing = next.get(gid) ?? [];
          next.set(gid, [...existing, { ts: Date.now(), event }].slice(-10));
          return next;
        });
      }
    },
    [expanded, onToggleGame],
  );
  useDaemonEvents(onEvent);

  // Cancel any in-flight verify on route unmount handled inside useVerifyFlow's cancel.

  if (status === "loading") {
    return (
      <main className={styles.main}>
        <Nav />
        <LoadingSpinner label="Loading audit view" />
      </main>
    );
  }

  // Daemon-down branch must precede the games-loading branch — otherwise the
  // LoadingSpinner masks the empty state when `games` is null because the
  // games-load effect only runs on `status === "running"`. WEB-UI-C-001.
  if (status !== "running" || !config) {
    return (
      <main className={styles.main}>
        <Nav />
        <EmptyState
          title="Daemon not running"
          body={
            <>
              Run <code>sov daemon start</code> in your terminal to begin verifying anchored proofs.
            </>
          }
        />
        {daemonError ? (
          <p className={styles.error} role="alert">
            {daemonError}
          </p>
        ) : null}
      </main>
    );
  }

  if (games === null) {
    return (
      <main className={styles.main}>
        <Nav />
        <LoadingSpinner label="Loading audit view" />
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <Nav />

      <header className={styles.header}>
        <h1>Audit Viewer</h1>
        <div className={styles.pills}>
          <Pill variant="neutral">network: {config.network}</Pill>
          <Pill variant="success" live>
            ● daemon
          </Pill>
        </div>
      </header>

      <p className={styles.intro}>Games ({games.length})</p>

      {games.length === 0 ? (
        <EmptyState
          title="No games yet"
          body={
            <>
              Start one with <code>sov play campfire_v1</code> in your terminal.
            </>
          }
        />
      ) : (
        <div className={styles.list}>
          {games.map((g) => (
            <GameRow
              key={g.summary.game_id}
              game={g}
              events={eventsForGame.get(g.summary.game_id) ?? []}
              onToggle={onToggleGame}
            />
          ))}
        </div>
      )}
    </main>
  );
}

function Nav() {
  return (
    <nav aria-label="primary">
      <Link to="/">Home</Link>
      <Link to="/audit" aria-current="page">
        Audit
      </Link>
      <Link to="/game">Game</Link>
      <Link to="/settings">Settings</Link>
    </nav>
  );
}

interface GameRowProps {
  game: GameSection;
  events: FeedEntry[];
  onToggle: (gameId: string, open: boolean) => void | Promise<void>;
}

function GameRow({ game, events, onToggle }: GameRowProps) {
  const verify = useVerifyFlow();
  const gameId = game.summary.game_id;

  // Cancel verify on unmount (cancel-on-navigate-away per spec §2).
  useEffect(() => {
    return () => {
      verify.cancel();
    };
  }, [verify.cancel]);

  const summarize = useMemo(() => {
    if (!game.rounds) {
      return `${game.summary.current_round} round${game.summary.current_round === 1 ? "" : "s"}`;
    }
    const total = game.rounds.length;
    const pending = game.rounds.filter((r) => r.status.anchor_status === "pending").length;
    const missing = game.rounds.filter((r) => r.status.anchor_status === "missing").length;
    if (missing > 0) return `${total} rounds · ${missing} missing`;
    if (pending > 0) return `${total} rounds · ${pending} pending`;
    return `${total} rounds · all anchored`;
  }, [game.rounds, game.summary.current_round]);

  const summaryHeader = (
    <span className={styles.summaryRow}>
      <span className={styles.gameId}>{game.summary.game_id}</span>
      <span className={styles.muted}>{game.summary.ruleset}</span>
      <span className={styles.muted}>{summarize}</span>
    </span>
  );

  return (
    <ExpandableRow
      summary={summaryHeader}
      onToggle={(open) => {
        void onToggle(gameId, open);
      }}
    >
      {game.loading ? (
        <LoadingSpinner label="Loading rounds" />
      ) : !game.rounds || game.rounds.length === 0 ? (
        <p className={styles.muted}>No rounds yet.</p>
      ) : (
        <>
          <table className={styles.roundsTable}>
            <thead>
              <tr>
                <th>Round</th>
                <th>Anchor</th>
                <th>txid</th>
                <th>Verify</th>
              </tr>
            </thead>
            <tbody>
              {game.rounds.map((r) => (
                <RoundRowView
                  key={r.round}
                  row={r}
                  verifyState={verify.perRound.get(r.round) ?? { kind: "idle" }}
                />
              ))}
            </tbody>
          </table>

          <div className={styles.verifyBar}>
            <button
              type="button"
              aria-busy={verify.isRunning}
              disabled={verify.isRunning || !game.rounds}
              onClick={() => {
                if (!game.rounds) return;
                void verify.start(
                  gameId,
                  game.rounds.map((r) => r.round),
                );
              }}
            >
              {verify.isRunning ? "Verifying…" : "Verify all rounds"}
            </button>
            {verify.isRunning ? (
              <button type="button" onClick={verify.cancel}>
                Cancel
              </button>
            ) : null}
            <span aria-live="polite" className={styles.verifyStatus}>
              {verify.isRunning && verify.currentRound
                ? `Verifying round ${verify.currentRound}…`
                : ""}
            </span>
          </div>

          {events.length > 0 ? (
            <div className={styles.gameEvents}>
              <h4 className={styles.h4}>Recent events for {gameId}</h4>
              <EventFeed events={events} limit={10} />
            </div>
          ) : null}
        </>
      )}
    </ExpandableRow>
  );
}

function RoundRowView({ row, verifyState }: { row: RoundRow; verifyState: RoundVerifyState }) {
  const status = row.status;
  const txid = status.txid ?? "";
  const txidShort = txid.length > 8 ? `${txid.slice(0, 4)}…${txid.slice(-2)}` : txid || "—";
  const anchorIcon =
    status.anchor_status === "anchored" ? "✓" : status.anchor_status === "pending" ? "⊘" : "✗";
  const anchorVariant =
    status.anchor_status === "anchored"
      ? "success"
      : status.anchor_status === "pending"
        ? "warn"
        : "error";

  let verifyCell: React.ReactNode = "—";
  if (verifyState.kind === "verifying") {
    verifyCell = <Pill variant="neutral">⋯</Pill>;
  } else if (verifyState.kind === "verified") {
    verifyCell = (
      <Pill variant="success" title="verified">
        ✓
      </Pill>
    );
  } else if (verifyState.kind === "failed") {
    // WEB-UI-C-005 / C-006: render human copy + recovery hint, not the raw
    // enum identifier the state machine uses internally.
    const display = verifyFailureDisplay(verifyState.reason);
    verifyCell = (
      <Pill variant="error" title={display.detail}>
        ✗ {display.short}
      </Pill>
    );
  }

  // WEB-UI-C-005: title-case display copy for the anchor pill (was raw enum).
  const anchorLabel = anchorStatusDisplay(status.anchor_status);

  return (
    <tr>
      <td>{row.round}</td>
      <td>
        <Pill variant={anchorVariant} title={anchorLabel}>
          <span aria-label={`anchor status: ${anchorLabel}`}>
            {anchorIcon} {anchorLabel}
          </span>
        </Pill>
      </td>
      <td>
        {txid && isSafeExplorerUrl(row.explorerUrl) ? (
          <a href={row.explorerUrl} target="_blank" rel="noreferrer noopener">
            {txidShort}
          </a>
        ) : (
          <span className={styles.muted}>{txidShort}</span>
        )}
      </td>
      <td>{verifyCell}</td>
    </tr>
  );
}
