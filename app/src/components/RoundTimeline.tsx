// RoundTimeline — horizontal dots: ● complete, ◐ active, ○ pending.
// Per spec §3 round timeline.

import styles from "./RoundTimeline.module.css";

export interface RoundTimelineProps {
  /** Total rounds in the game (state.config.max_rounds). */
  total: number;
  /** Currently active round (state.current_round). 1-indexed. */
  current: number;
  /** True when game is over — all dots filled regardless of current. */
  gameOver?: boolean;
}

export function RoundTimeline({ total, current, gameOver = false }: RoundTimelineProps) {
  const dots = Array.from({ length: total }, (_, i) => {
    const round = i + 1;
    if (gameOver || round < current) return { round, kind: "complete" as const };
    if (round === current) return { round, kind: "active" as const };
    return { round, kind: "pending" as const };
  });

  return (
    <div
      className={styles.timeline}
      role="img"
      aria-label={`Round ${current} of ${total}${gameOver ? " (game over)" : ""}`}
    >
      <div className={styles.dots}>
        {dots.map((d) => (
          <span
            key={d.round}
            className={`${styles.dot} ${styles[d.kind]}`}
            aria-hidden="true"
            data-kind={d.kind}
          >
            {d.kind === "complete" ? "●" : d.kind === "active" ? "◐" : "○"}
          </span>
        ))}
      </div>
      <div className={styles.labels} aria-hidden="true">
        <span>1</span>
        <span>{total}</span>
      </div>
    </div>
  );
}
