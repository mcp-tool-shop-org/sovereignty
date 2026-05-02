// Reusable empty-state per spec §9. Title + body + optional CTA + optional glyph.
//
// Stage 9-D Theme 4 (WEB-UI-D-013):
//   - `glyph?: ReactNode` slot for inline SVG semantic anchor. Mike's lock:
//     SVG-INLINE only (no image assets). Theme alignment via `currentColor`,
//     accessibility via role="img" + aria-label on each glyph.
//   - Three named glyphs exported (EmptyBoxGlyph / PausedGameGlyph /
//     DisconnectedPlugGlyph) for the three semantic empty states surfaced
//     across routes; total bundle delta ~900 bytes against a 245KB bundle.

import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

export interface EmptyStateProps {
  title: string;
  body?: ReactNode;
  cta?: ReactNode;
  /** Optional inline SVG / unicode glyph rendered above the title.
   *  Theme-aligned via currentColor; theme.css owns the palette. */
  glyph?: ReactNode;
}

export function EmptyState({ title, body, cta, glyph }: EmptyStateProps) {
  return (
    <section className={styles.root} aria-label="empty state">
      {glyph ? <div className={styles.glyph}>{glyph}</div> : null}
      <h2 className={styles.title}>{title}</h2>
      {body ? <div className={styles.body}>{body}</div> : null}
      {cta ? <div className={styles.cta}>{cta}</div> : null}
    </section>
  );
}

/** "No content" glyph — empty open box. Used for "no games yet" / "no rounds
 *  yet" empty states across Audit and similar list-empty surfaces. */
export function EmptyBoxGlyph() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label="empty box"
    >
      <path d="M3 8l9-5 9 5v8l-9 5-9-5V8z" />
      <path d="M3 8l9 5 9-5" />
      <path d="M12 13v8" />
    </svg>
  );
}

/** "No active flow" glyph — paused / play indicator. Used for "no active
 *  game" empty state. */
export function PausedGameGlyph() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label="paused game"
    >
      <circle cx="12" cy="12" r="9" />
      <line x1="10" y1="9" x2="10" y2="15" />
      <line x1="14" y1="9" x2="14" y2="15" />
    </svg>
  );
}

/** "Disconnected" glyph — unplugged cable. Used for "daemon not running"
 *  empty states across Audit / Game / Settings. */
export function DisconnectedPlugGlyph() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label="disconnected"
    >
      <path d="M9 2v4" />
      <path d="M15 2v4" />
      <path d="M7 6h10v4a5 5 0 0 1-2.5 4.33" />
      <path d="M9.5 14.33A5 5 0 0 1 7 10V6" />
      <line x1="3" y1="3" x2="21" y2="21" />
    </svg>
  );
}
