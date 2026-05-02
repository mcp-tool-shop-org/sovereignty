#!/usr/bin/env bash
# scripts/check-voice.sh — Stage C voice anti-pattern gate (CI-TOOLING-C-001).
#
# Scope per Wave 8 dispatch brief Pin A:
#   please / you should / you might / oops / whoops / sorry  (everywhere)
#   trailing "!" inside double-quoted strings  (error files only — errors are
#                                               statements, not exclamations)
#   emoji codepoints inside double-quoted strings  (error files only)
#
# Game flavor text (e.g. campfire deck strings, win-condition narration)
# legitimately uses "!". Typographic em-dashes (—) and smart quotes are
# intentional and out of scope — they're typography, not voice.
#
# Scan dirs: sov_engine/, sov_transport/, sov_cli/, sov_daemon/, app/src/
# Error files (narrower !"/emoji scope):
#   sov_cli/errors.py
#   app/src-tauri/src/commands.rs (ShellError Display impls)
#
# Exempt: code comments (# // /* *), tests/, app/src/test/, this script itself.
#
# Tooling: prefers ripgrep (rg) when available; falls back to POSIX grep -E.
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
  echo "[check-voice] ripgrep (rg) not found; falling back to grep -rE." >&2
fi

# ---------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------
SCAN_DIRS=()
for d in sov_engine sov_transport sov_cli sov_daemon app/src; do
  [ -d "$d" ] && SCAN_DIRS+=("$d")
done

if [ "${#SCAN_DIRS[@]}" -eq 0 ]; then
  echo "[check-voice] No scan directories present; nothing to do." >&2
  exit 0
fi

# Files where `!"` and emoji are voice anti-patterns (error contexts).
# Other files (game flavor, route titles) legitimately use exclamations.
ERROR_FILES=()
for f in sov_cli/errors.py app/src-tauri/src/commands.rs app/src-tauri/src/error.rs; do
  [ -f "$f" ] && ERROR_FILES+=("$f")
done

RG_IGNORES=(
  --glob '!tests/**'
  --glob '!app/src/test/**'
  --glob '!**/__pycache__/**'
  --glob '!**/*.pyc'
  --glob '!**/node_modules/**'
  --glob '!**/dist/**'
  --glob '!scripts/check-voice.sh'
)

# Word-bounded prose anti-patterns (case-insensitive).
WORD_PATTERN='\b(please|you should|you might|oops|whoops|sorry)\b'

# Trailing "!" inside double-quoted strings — only flagged inside error files.
BANG_PATTERN='"[^"\\]*!"'

# Emoji-codepoint detection was previously regex-based but the
# ``[\xF0\x9F]`` character-class form interprets differently across rg
# versions (macOS-builtin vs Linux distro builds), false-firing on
# pure-ASCII content lines on Linux runners. Same retrospective as
# Pin A's ``!``/em-dash false-fire — over-aggressive heuristic without
# cross-platform validation. Emoji-in-error-message is rare (humans
# spot it in code review); the ``please|you should|...`` word patterns
# are the load-bearing Pin A piece. Drop emoji-codepoint check; if it
# surfaces as a real recurring issue, replace with a Python AST/byte
# walker that's deterministic across runners.

COMMENT_FILTER='^[^:]+:[0-9]+:[[:space:]]*(#|//|\*|/\*)'

HITS_FILE="$(mktemp)"
trap 'rm -f "$HITS_FILE"' EXIT

run_word_pattern() {
  if [ "$TOOL" = "rg" ]; then
    rg --line-number --no-heading --color=never -i \
       "${RG_IGNORES[@]}" \
       "$WORD_PATTERN" "${SCAN_DIRS[@]}" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | sed "s|^|[voice-word] |" >> "$HITS_FILE" || true
  else
    grep -rEni \
         --exclude-dir=tests --exclude-dir=__pycache__ \
         --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=test \
         --exclude='check-voice.sh' \
         "$WORD_PATTERN" "${SCAN_DIRS[@]}" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | sed "s|^|[voice-word] |" >> "$HITS_FILE" || true
  fi
}

run_error_file_pattern() {
  local label="$1"
  local pattern="$2"
  [ "${#ERROR_FILES[@]}" -eq 0 ] && return 0

  if [ "$TOOL" = "rg" ]; then
    rg --line-number --no-heading --color=never \
       "$pattern" "${ERROR_FILES[@]}" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | sed "s|^|[$label] |" >> "$HITS_FILE" || true
  else
    grep -En "$pattern" "${ERROR_FILES[@]}" 2>/dev/null \
      | grep -Ev "$COMMENT_FILTER" \
      | sed "s|^|[$label] |" >> "$HITS_FILE" || true
  fi
}

run_word_pattern
run_error_file_pattern "trailing-!" "$BANG_PATTERN"

if [ -s "$HITS_FILE" ]; then
  echo ""
  echo "Stage C voice gate failed. Anti-patterns surface in user-facing"
  echo "strings. Code comments and test fixtures are exempt."
  echo ""
  cat "$HITS_FILE"
  echo ""
  echo "[check-voice] FAIL — $(wc -l < "$HITS_FILE" | tr -d ' ') hit(s)"
  exit 1
fi

echo "[check-voice] OK — no anti-patterns surfaced."
exit 0
