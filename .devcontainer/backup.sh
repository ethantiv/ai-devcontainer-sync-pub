#!/bin/bash
# DevContainer volume backup — create/restore encrypted backups of mounted volumes
# Usage: .devcontainer/backup.sh <create|restore|list> [options]

set -euo pipefail

# ── Helpers ──────────────────────────────────────────────
ok()   { echo -e "  \033[32m✔︎\033[0m $1"; }
warn() { echo -e "  \033[33m⚠️\033[0m  $1"; }
fail() { echo -e "  \033[31m❌\033[0m $1"; }

usage() {
    cat <<'EOF'
Usage: .devcontainer/backup.sh <command> [options]

Commands:
  create              Create encrypted backup of DevContainer volumes
  restore <file>      Restore volumes from encrypted backup
  list                List existing backups

Options (restore):
  --force             Skip confirmation prompt

Environment:
  BACKUP_PIN          PIN for encryption/decryption (required for create, optional for restore)
EOF
}

# ── Configuration ────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Overridable for testing
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
BACKUP_SOURCE_PATHS="${BACKUP_SOURCE_PATHS:-/home/vscode/.claude /home/vscode/.gemini /home/vscode/.cache/google-vscode-extension/auth}"

# ── Command router ───────────────────────────────────────
cmd_create() { echo "TODO"; }
cmd_restore() { echo "TODO"; }
cmd_list() { echo "TODO"; }

case "${1:-}" in
    create)  shift; cmd_create "$@" ;;
    restore) shift; cmd_restore "$@" ;;
    list)    shift; cmd_list "$@" ;;
    *)       usage; exit 1 ;;
esac
