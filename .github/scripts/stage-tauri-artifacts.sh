#!/usr/bin/env bash
# Copy Tauri bundle outputs into dist/ using locked sovereignty-app-* names.
# ARTIFACT_GLOBS is bound via env (not unquoted ${{ matrix.artifacts }} interpolation)
# so a YAML `|` newline cannot split `for glob in ...; do` (F-04ad0b5c).
set -euo pipefail

: "${ARTIFACT_GLOBS:?ARTIFACT_GLOBS is required}"
: "${BUNDLE_BASE:?BUNDLE_BASE is required}"
: "${TARGET:?TARGET is required}"

VERSION="${VERSION:-${GITHUB_REF_NAME:-}}"
VERSION="${VERSION#v}"
if [ -z "$VERSION" ]; then
  echo "::error::VERSION is empty (expected v* tag or RELEASE_TAG)"
  exit 1
fi

mkdir -p dist
shopt -s nullglob

# Map compound updater suffixes; last-dot would collide .sig / .gz (F-03b6a7c0).
suffix_of() {
  local base
  base="$(basename "$1")"
  case "$base" in
    *.app.tar.gz.sig) echo "app.tar.gz.sig" ;;
    *.app.tar.gz) echo "app.tar.gz" ;;
    *.AppImage.tar.gz.sig) echo "AppImage.tar.gz.sig" ;;
    *.AppImage.tar.gz) echo "AppImage.tar.gz" ;;
    *.AppImage.sig) echo "AppImage.sig" ;;
    *.msi.zip.sig) echo "msi.zip.sig" ;;
    *.msi.zip) echo "msi.zip" ;;
    *.msi.sig) echo "msi.sig" ;;
    *.dmg.sig) echo "dmg.sig" ;;
    *.deb.sig) echo "deb.sig" ;;
    *.nsis.zip.sig) echo "nsis.zip.sig" ;;
    *.nsis.zip) echo "nsis.zip" ;;
    *.exe.sig) echo "exe.sig" ;;
    *) echo "${base##*.}" ;;
  esac
}

# Space- or newline-separated globs. Quote the source so `*` is not expanded here.
while IFS= read -r glob || [ -n "${glob:-}" ]; do
  glob="${glob//$'\r'/}"
  glob="${glob#"${glob%%[![:space:]]*}"}"
  glob="${glob%"${glob##*[![:space:]]}"}"
  [ -z "$glob" ] && continue
  for src in "${BUNDLE_BASE}"/${glob}; do
    [ -e "$src" ] || continue
    ext="$(suffix_of "$src")"
    outname="sovereignty-app-${VERSION}-${TARGET}.${ext}"
    cp "$src" "dist/${outname}"
    echo "Staged: dist/${outname}"
  done
done < <(printf '%s\n' "$ARTIFACT_GLOBS" | tr ' ' '\n')

echo "Staged dist/ contents:"
ls -la dist/ || true
if [ -z "$(ls -A dist 2>/dev/null || true)" ]; then
  echo "::error::no Tauri artifacts staged"
  exit 1
fi
