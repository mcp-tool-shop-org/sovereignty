// Status pill — matches the v2.1 spec §9 table.
// Use <span role="status"> for live regions (spec §1: status pill semantic).

import styles from "./Pill.module.css";

export type PillVariant = "neutral" | "success" | "warn" | "error" | "accent";

export interface PillProps {
  variant?: PillVariant;
  /** When true, renders with role="status" for screen-reader live region announcements. */
  live?: boolean;
  children: React.ReactNode;
  title?: string;
}

export function Pill({ variant = "neutral", live = false, children, title }: PillProps) {
  // WEB-UI-D-024: when `live`, attach `.live` class so the pulsing dot
  // pseudo-element renders for sighted users (sibling to the role="status"
  // SR semantic). Reduced-motion handled in CSS.
  const cls = `${styles.pill} ${styles[variant] ?? ""} ${live ? styles.live : ""}`.trim();
  // WEB-UI-D-027: mirror title into aria-label so screen-reader users hear
  // the detail copy. `title` alone is hover-only on mouse — the audit-row
  // failure-detail pill is exactly the user who needs the copy most.
  const ariaLabel = title;
  // Spec §1 mandates `<span role="status">` for live-region pills. Biome's
  // useSemanticElements rule prefers `<output>` for role="status"; both have
  // identical screen-reader behavior. Honor the spec.
  return live ? (
    // biome-ignore lint/a11y/useSemanticElements: spec §1 mandates span role="status"
    <span className={cls} role="status" title={title} aria-label={ariaLabel}>
      {children}
    </span>
  ) : (
    <span className={cls} title={title} aria-label={ariaLabel}>
      {children}
    </span>
  );
}
