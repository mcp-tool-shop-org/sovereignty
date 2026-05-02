// ExpandableRow — wraps native <details><summary> with consistent styling.
// Spec §1: must use semantic <details>, NOT <div onClick toggle>.

import type { ReactNode } from "react";
import styles from "./ExpandableRow.module.css";

export interface ExpandableRowProps {
  /** Summary content rendered inside <summary>. */
  summary: ReactNode;
  /** Body rendered after the summary when expanded. */
  children: ReactNode;
  /** Default open state. */
  defaultOpen?: boolean;
  /** Optional onToggle callback (mirrors native HTMLDetailsElement toggle). */
  onToggle?: (open: boolean) => void;
}

export function ExpandableRow({
  summary,
  children,
  defaultOpen = false,
  onToggle,
}: ExpandableRowProps) {
  return (
    <details
      className={styles.details}
      open={defaultOpen || undefined}
      onToggle={(e) => {
        if (onToggle) onToggle((e.currentTarget as HTMLDetailsElement).open);
      }}
    >
      <summary className={styles.summary}>{summary}</summary>
      <div className={styles.body}>{children}</div>
    </details>
  );
}
