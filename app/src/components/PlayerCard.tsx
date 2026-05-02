// PlayerCard — primitives + ruleset-aware resources.
// Per spec §3 player resource cards. Resources row only renders for
// town_hall* rulesets (campfire omits to keep cards clean).
//
// CRITICAL: primitive is `coins` not `votes`. Field names match
// sov_engine/models.py PlayerState exactly.

import type { PlayerState } from "../types/game";
import { isTownHall } from "../types/game";
import styles from "./PlayerCard.module.css";

export interface PlayerCardProps {
  player: PlayerState;
  ruleset: string;
}

export function PlayerCard({ player, ruleset }: PlayerCardProps) {
  const showResources = isTownHall(ruleset);
  return (
    <article className={styles.card} aria-label={`Player ${player.name}`}>
      <header className={styles.header}>{player.name}</header>
      <dl className={styles.grid}>
        <dt>coins</dt>
        <dd>{player.coins}</dd>
        <dt>reputation</dt>
        <dd>{player.reputation}</dd>
        <dt>upgrades</dt>
        <dd>{player.upgrades}</dd>
        <dt>vouchers</dt>
        <dd>{player.vouchers_held.length}</dd>
        <dt>deals</dt>
        <dd>{player.active_deals.length}</dd>
        <dt>treaties</dt>
        <dd>{player.active_treaties.length}</dd>
      </dl>
      {showResources ? (
        <div className={styles.resources} aria-label="resources">
          <h4 className={styles.resourcesTitle}>resources</h4>
          <dl className={styles.grid}>
            {Object.entries(player.resources)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([name, count]) => (
                <ResourceRow key={name} name={name} count={count} />
              ))}
          </dl>
        </div>
      ) : null}
    </article>
  );
}

function ResourceRow({ name, count }: { name: string; count: number }) {
  return (
    <>
      <dt>{name}</dt>
      <dd>{count}</dd>
    </>
  );
}
