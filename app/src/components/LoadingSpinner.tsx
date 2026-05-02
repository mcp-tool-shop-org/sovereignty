// Loading spinner — CSS animation only, no library. Per spec §9.
// aria-busy + role="progressbar" for screen readers.

import styles from "./LoadingSpinner.module.css";

export interface LoadingSpinnerProps {
  label?: string;
  size?: "sm" | "md";
}

export function LoadingSpinner({ label = "Loading", size = "md" }: LoadingSpinnerProps) {
  const cls = `${styles.spinner} ${size === "sm" ? styles.sm : styles.md}`;
  // Use role="status" (live region) instead of progressbar — spinner is
  // indeterminate; progressbar requires aria-valuenow/min/max.
  return (
    // biome-ignore lint/a11y/useSemanticElements: span+role=status preferred over <output> here
    <span className={styles.wrapper} role="status" aria-busy="true" aria-label={label}>
      <span className={cls} aria-hidden="true" />
      <span className={styles.label}>{label}…</span>
    </span>
  );
}
