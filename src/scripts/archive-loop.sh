#!/usr/bin/env bash
# Archive current plan and specs to docs/superpowers/archive/ without running loop.
set -euo pipefail

archive_plan() {
    local latest=""
    for f in docs/superpowers/plans/*.md; do
        [[ -f "$f" ]] || continue
        latest="$f"
    done
    [[ -z "$latest" ]] && { echo "[ARCHIVE] No plan to archive."; return 0; }

    local archive_dir="docs/superpowers/archive"
    mkdir -p "$archive_dir"
    mv "$latest" "$archive_dir/"
    echo "[ARCHIVE] Archived plan: $(basename "$latest")"

    for doc in docs/superpowers/specs/*.md; do
        [[ -f "$doc" ]] || continue
        mv "$doc" "$archive_dir/"
        echo "[ARCHIVE] Archived spec: $(basename "$doc")"
    done
}

archive_plan

if git rev-parse --is-inside-work-tree &>/dev/null; then
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        git add -A
        git commit -m "chore(loop): archive plan and specs" || true
    fi
fi
