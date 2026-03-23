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

# Ensure gpg-agent is fresh (stale sockets cause "can't connect" errors in containers)
gpgconf --kill gpg-agent 2>/dev/null || true

# ── Configuration ────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Overridable for testing
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
BACKUP_SOURCE_PATHS="${BACKUP_SOURCE_PATHS:-/home/vscode/.claude /home/vscode/.gemini /home/vscode/.cache/google-vscode-extension/auth}"

# ── Command router ───────────────────────────────────────
cmd_create() {
    # Validate PIN
    if [[ -z "${BACKUP_PIN:-}" ]]; then
        fail "BACKUP_PIN is not set. Add it to config/.env"
        exit 1
    fi

    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"

    # Ensure .gitignore has backup entry (defensive)
    local gitignore="$REPO_ROOT/.gitignore"
    if [[ -f "$gitignore" ]] && ! grep -q '.devcontainer/backups/' "$gitignore"; then
        echo -e "\n# Encrypted volume backups\n.devcontainer/backups/" >> "$gitignore"
        ok "Added .devcontainer/backups/ to .gitignore"
    fi

    # Build list of existing source paths
    local sources=()
    for path in $BACKUP_SOURCE_PATHS; do
        if [[ -d "$path" ]]; then
            sources+=("$path")
        else
            warn "Skipping missing folder: $path"
        fi
    done

    if [[ ${#sources[@]} -eq 0 ]]; then
        fail "No source folders found to backup"
        exit 1
    fi

    # Create temporary archive (global so trap can reference it)
    local timestamp
    timestamp="$(date +%Y-%m-%d-%H%M%S)"
    _TMP_ARCHIVE="$BACKUP_DIR/.backup-${timestamp}.tar.gz"
    local gpg_archive="$BACKUP_DIR/backup-${timestamp}.tar.gz.gpg"

    # Trap: always remove unencrypted temp file
    trap '[[ -n "${_TMP_ARCHIVE:-}" ]] && rm -f "$_TMP_ARCHIVE"' EXIT INT TERM

    # Tar with full absolute paths (tar strips leading / automatically)
    tar czf "$_TMP_ARCHIVE" "${sources[@]}" 2>/dev/null

    # Encrypt
    gpg --batch --yes --passphrase "$BACKUP_PIN" \
        --pinentry-mode loopback \
        --symmetric --cipher-algo AES256 \
        --output "$gpg_archive" "$_TMP_ARCHIVE"

    # Remove temp (also handled by trap, but be explicit)
    rm -f "$_TMP_ARCHIVE"
    _TMP_ARCHIVE=""

    local size
    size="$(du -h "$gpg_archive" | cut -f1)"
    ok "Backup created: $gpg_archive ($size)"
}
cmd_restore() {
    local force=false
    local file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force) force=true; shift ;;
            *)
                if [[ -z "$file" ]]; then file="$1"; shift
                else fail "Unknown argument: $1"; usage; exit 1; fi
                ;;
        esac
    done

    # Validate file argument
    if [[ -z "$file" ]]; then
        fail "Missing backup file argument"
        usage
        exit 1
    fi

    if [[ ! -f "$file" ]]; then
        fail "Backup file not found: $file"
        exit 1
    fi

    # Resolve PIN
    local pin="${BACKUP_PIN:-}"
    if [[ -z "$pin" ]]; then
        if [[ -t 0 ]]; then
            read -s -p "Enter backup PIN: " pin
            echo
        else
            fail "BACKUP_PIN is not set and no interactive terminal available"
            exit 1
        fi
    fi

    if [[ -z "$pin" ]]; then
        fail "PIN cannot be empty"
        exit 1
    fi

    # Confirmation prompt
    if [[ "$force" != true ]]; then
        if [[ -t 0 ]]; then
            read -p "Overwrite current config? [y/N] " confirm
            if [[ "$confirm" != [yY] ]]; then
                warn "Restore cancelled"
                exit 0
            fi
        else
            fail "Use --force to skip confirmation in non-interactive mode"
            exit 1
        fi
    fi

    # Restore target (overridable for testing)
    local restore_root="${BACKUP_RESTORE_ROOT:-/}"

    # Decrypt and extract
    if ! gpg --batch --yes --passphrase "$pin" --pinentry-mode loopback --decrypt "$file" 2>/dev/null \
        | tar xzf - -C "$restore_root"; then
        fail "Restore failed — wrong PIN or corrupted backup"
        exit 1
    fi

    ok "Restore completed from: $file"
}

cmd_list() {
    if [[ ! -d "$BACKUP_DIR" ]] || [[ -z "$(ls "$BACKUP_DIR"/*.tar.gz.gpg 2>/dev/null)" ]]; then
        warn "No backups found in $BACKUP_DIR"
        return 0
    fi

    echo "Backups in $BACKUP_DIR:"
    echo ""
    ls -lh "$BACKUP_DIR"/*.tar.gz.gpg | awk '{print "  " $NF " (" $5 ", " $6 " " $7 " " $8 ")"}'
}

case "${1:-}" in
    create)  shift; cmd_create "$@" ;;
    restore) shift; cmd_restore "$@" ;;
    list)    shift; cmd_list "$@" ;;
    *)       usage; exit 1 ;;
esac
