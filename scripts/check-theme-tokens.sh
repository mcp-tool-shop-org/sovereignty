#!/usr/bin/env bash
# scripts/check-theme-tokens.sh — Stage D theme-token discipline gate
# (CI-TOOLING-D-001).
#
# Scope per Wave 9 dispatch brief Pin D:
#   bare hex (#xxx, #xxxx, #xxxxxx, #xxxxxxxx) and bare rgb()/rgba()
#   inside app/src/**/*.{tsx,module.css}  →  flagged
#
# Theme is the single source of truth. app/src/styles/theme.css defines
# tokens (--sov-*); everywhere else references them.  Allowed by design:
#   var(--sov-*)
#   color-mix(in srgb, var(--sov-*) ...) — `srgb` does NOT match
#       \brgba?\( (next char is a comma, not a paren), so the allowlist
#       here is automatic
#   transparent / currentColor / inherit / initial / unset / none —
#       never matched the detect patterns anyway (documentary)
#   /* legacy: #f00 */ — inline-comment migration markers, explicitly
#       exempt so agents can mark known deprecations awaiting cleanup
#
# Exempt files:
#   app/src/styles/theme.css (the source of truth)
#   tests, snapshots, node_modules, dist
#
# Don't reach into app/src-tauri/ (Tauri config, not CSS).
#
# Critical lesson from Pin A (check-voice.sh): the over-aggressive
# `!`/em-dash false-fire was the failure mode. Pin D's allowlist must
# be wide enough to NOT false-fire on theme-aligned-but-not-literal-var
# derivations (notably `color-mix(in srgb, var(--sov-*) ...)`, in use
# at ~7 sites across Pill / DaemonDisconnectedBanner / ConfirmDialog /
# Settings).
#
# Tooling: prefers ripgrep (rg); falls back to POSIX grep -E.
# Exit 0 = clean. Exit 1 = hits, with file:line:match printed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ---------------------------------------------------------------------
# Tooling detection
# ---------------------------------------------------------------------
if command -v rg >/dev/null 2>&1; then
  TOOL=rg
else
  TOOL=grep
  echo "[check-theme-tokens] ripgrep (rg) not found; falling back to grep -rE." >&2
fi

# ---------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------
SCAN_DIR="app/src"
if [ ! -d "$SCAN_DIR" ]; then
  echo "[check-theme-tokens] $SCAN_DIR not present; nothing to do." >&2
  exit 0
fi

# Bare hex: 3, 4, 6, or 8 hex chars after #. Word boundary at the end
# so trailing tokens don't bleed into the match.
HEX_PATTERN='#[0-9a-fA-F]{3,8}\b'

# Bare rgb()/rgba(): the \b word boundary in front matters — it ensures
# the literal `rgb` substring inside `srgb` does NOT match
# (`color-mix(in srgb, var(--sov-bg) 90%, #000)` is theme-aligned,
# the trailing `,` after `srgb` keeps it from matching `\brgba?\(`).
RGBFN_PATTERN='\brgba?\s*\('

# Comments (CSS /* */ and TSX //) are exempt. Migration marker
# /* legacy: ... */ explicitly exempt as well — agents can mark known
# deprecations awaiting cleanup.
COMMENT_FILTER='^[^:]+:[0-9]+:[[:space:]]*(//|\*|/\*)'
LEGACY_FILTER='/\* legacy:'

HITS_FILE="$(mktemp)"
trap 'rm -f "$HITS_FILE"' EXIT

run_pattern() {
  local label="$1"
  local pattern="$2"

  if [ "$TOOL" = "rg" ]; then
    rg --line-number --no-heading --color=never \
       --glob 'app/src/**/*.tsx' \
       --glob 'app/src/**/*.module.css' \
       --glob '!app/src/styles/theme.css' \
       --glob '!**/*.test.*' \
       --glob '!**/*.snap' \
       --glob '!**/node_modules/**' \
       --glob '!**/dist/**' \
       "$pattern" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | grep -v "$LEGACY_FILTER" \
      | sed "s|^|[$label] |" >> "$HITS_FILE" || true
  else
    # POSIX fallback: walk app/src/.
    find app/src -type f \( -name '*.tsx' -o -name '*.module.css' \) \
      ! -path 'app/src/styles/theme.css' \
      ! -name '*.test.*' \
      ! -name '*.snap' \
      ! -path '*/node_modules/*' \
      ! -path '*/dist/*' \
      -print0 \
      | xargs -0 grep -En "$pattern" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | grep -v "$LEGACY_FILTER" \
      | sed "s|^|[$label] |" >> "$HITS_FILE" || true
  fi
}

run_pattern "bare-hex" "$HEX_PATTERN"
run_pattern "bare-rgb" "$RGBFN_PATTERN"

if [ -s "$HITS_FILE" ]; then
  echo ""
  echo "Stage D theme-token gate failed. Bare colors surface outside"
  echo "app/src/styles/theme.css. Single source of truth: theme.css."
  echo "Reference via var(--sov-*); CSS keywords + color-mix(in srgb,"
  echo "var(--sov-*) ...) + /* legacy: */ markers all pass."
  echo ""
  cat "$HITS_FILE"
  echo ""
  echo "[check-theme-tokens] FAIL — $(wc -l < "$HITS_FILE" | tr -d ' ') hit(s)"
  exit 1
fi

echo "[check-theme-tokens] OK — no theme-token drift."
exit 0
