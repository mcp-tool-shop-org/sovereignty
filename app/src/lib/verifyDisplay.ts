// verifyDisplay — maps internal RoundVerifyState reasons to user-facing copy.
//
// Stage 8-C WEB-UI-C-005 + C-006: the per-round verify pill was rendering
// the raw enum identifier (e.g. "✗ envelope_mismatch") which is internal
// state-machine vocabulary, not language a player can act on. This helper
// returns the short pill body, hover-tooltip detail, and (where the daemon
// vs chain path differ) the recovery copy.

import type { AnchorStatus } from "../types/daemon";

export type VerifyFailureReason =
  | "envelope_mismatch"
  | "not_on_chain"
  | "daemon_unreachable"
  | "chain_unreachable";

export interface VerifyDisplay {
  /** Short label rendered inside the pill body. */
  short: string;
  /** Long-form copy used on the pill `title` (hover tooltip). */
  detail: string;
}

/** Map a verify-flow failure reason to display copy. */
export function verifyFailureDisplay(reason: VerifyFailureReason): VerifyDisplay {
  switch (reason) {
    case "envelope_mismatch":
      return {
        short: "envelope mismatch",
        detail:
          "Recomputed envelope hash didn't match the proof file. The proof may have been modified.",
      };
    case "not_on_chain":
      return {
        short: "not on chain",
        detail:
          "anchors.json shows this round as anchored, but the chain lookup didn't find the tx. Run `sov anchor` to retry.",
      };
    case "daemon_unreachable":
      return {
        short: "daemon unreachable",
        detail: "Daemon unreachable. Run `sov daemon status --json` to inspect.",
      };
    case "chain_unreachable":
      return {
        short: "chain unreachable",
        detail: "Chain unreachable. Retry, or run `sov verify --tx <hash>`.",
      };
  }
}

export type BrowseAnchorVariant = "success" | "warn" | "error";

export interface BrowseAnchorVisual {
  icon: string;
  variant: BrowseAnchorVariant;
}

/** Map an AnchorStatus to local-index vocabulary for the Audit browse
 *  column. `/anchor-status` never hits XRPL — reserve "Verified" /
 *  "Not on chain" for `useVerifyFlow` results. F-7f7091d3. */
export function anchorStatusDisplay(status: AnchorStatus): string {
  switch (status) {
    case "anchored":
      return "Anchored";
    case "pending":
      return "Pending";
    case "missing":
      return "No local anchor";
  }
}

/** Icon + pill variant for the browse Anchor column. Shared with the
 *  wire-shape pin so Audit.tsx cannot drift back to a copied ternary. */
export function browseAnchorVisual(status: AnchorStatus): BrowseAnchorVisual {
  switch (status) {
    case "anchored":
      return { icon: "✓", variant: "success" };
    case "pending":
      return { icon: "⊘", variant: "warn" };
    case "missing":
      return { icon: "✗", variant: "error" };
  }
}
