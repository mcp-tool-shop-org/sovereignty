// Reusable empty-state per spec §9. Title + body + optional CTA.

import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

export interface EmptyStateProps {
  title: string;
  body?: ReactNode;
  cta?: ReactNode;
}

export function EmptyState({ title, body, cta }: EmptyStateProps) {
  return (
    <section className={styles.root} aria-label="empty state">
      <h2 className={styles.title}>{title}</h2>
      {body ? <div className={styles.body}>{body}</div> : null}
      {cta ? <div className={styles.cta}>{cta}</div> : null}
    </section>
  );
}
