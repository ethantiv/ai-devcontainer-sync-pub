#!/bin/bash

# Autonomous development loop powered by Claude CLI
# Part of ai-devcontainer-sync

# Resolve script directory (works with symlinks)
LOOP_SCRIPTS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LOOP_ROOT="$(dirname "$LOOP_SCRIPTS_DIR")"

# Resolve claude binary (prefer ~/.claude/bin, fall back to PATH)
CLAUDE_CMD="${HOME}/.claude/bin/claude"
[[ -x "$CLAUDE_CMD" ]] || CLAUDE_CMD="$(command -v claude 2>/dev/null || true)"
[[ -x "$CLAUDE_CMD" ]] || { echo "[ERROR] Claude CLI not found" >&2; exit 1; }
claude() { "$CLAUDE_CMD" "$@"; }

# Tracking variables
START_TIME=$(date +%s)
EXIT_STATUS="interrupted"

# Cleanup function - called on exit
cleanup() {
    echo ""
    echo "[CLEANUP] Done."
}

# Trap handlers
trap cleanup EXIT SIGINT SIGTERM SIGHUP

# Default values
LOG_DIR="loop/logs"
SCRIPT_NAME="run"
AUTONOMOUS=false
IDEA=""
NEW_CYCLE=false
CONTEXT_WINDOW=200000
CTX_FILE=""

# Help function
usage() {
    echo "Usage: $0 [-d] [-a] [-n] [-i idea]"
    echo ""
    echo "Options:"
    echo "  -d              Design mode (interactive brainstorming)"
    echo "  -a              Autonomous mode (default: interactive)"
    echo "  -n              Archive completed plan and start fresh"
    echo "  -i text         Seed idea written to docs/IDEA.md"
    echo "  -h              Show this help"
    exit 0
}

# Find the current (most recent) plan file in docs/superpowers/plans/
find_current_plan() {
    local latest=""
    for f in docs/superpowers/plans/*-plan.md; do
        [[ -f "$f" ]] || continue
        latest="$f"
    done
    echo "$latest"
}

# Check if plan is complete (for archive_completed_plan)
check_completion() {
    local plan
    plan=$(find_current_plan)
    [[ -z "$plan" || ! -f "$plan" ]] && return 1

    local unchecked pending_phases complete_marker
    unchecked=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]\]' "$plan" 2>/dev/null) || unchecked=0
    pending_phases=$(grep -ciE '\*{0,2}Status\*{0,2}:\*{0,2}\s*(pending|in.progress)' "$plan" 2>/dev/null) || pending_phases=0
    complete_marker=$(grep -cE '\*{0,2}Status\*{0,2}:\*{0,2}\s*(COMPLETE|DONE)|BUILD COMPLETE|PLAN COMPLETE' "$plan" 2>/dev/null) || complete_marker=0

    [[ "$unchecked" -eq 0 && "$pending_phases" -eq 0 && "$complete_marker" -gt 0 ]]
}

# Archive a completed plan and related specs to docs/superpowers/archive/
archive_completed_plan() {
    local plan
    plan=$(find_current_plan)
    [[ -z "$plan" || ! -f "$plan" ]] && { echo "[NEW] No plan to archive."; return 0; }

    if ! check_completion; then
        echo "[NEW] Plan is not complete — cannot archive. Continue with current plan."
        return 1
    fi

    local archive_dir="docs/superpowers/archive"
    mkdir -p "$archive_dir"
    mv "$plan" "$archive_dir/"
    echo "[NEW] Archived completed plan to $archive_dir/$(basename "$plan")"

    for doc in docs/superpowers/specs/*-design.md; do
        [[ -f "$doc" ]] || continue
        mv "$doc" "$archive_dir/"
        echo "[NEW] Archived design doc: $(basename "$doc")"
    done

    return 0
}

# Post-run git safety net — auto-commit if agent skipped git
ensure_committed() {
    git rev-parse --is-inside-work-tree &>/dev/null || return 0
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        echo -e "\n[LOOP] Uncommitted changes detected — auto-committing..."
        git add -A
        git commit -m "chore(loop): auto-commit after run (agent skipped commit)" || true
        git push 2>/dev/null || true
    fi
    local untracked
    untracked=$(git ls-files --others --exclude-standard 2>/dev/null | head -1)
    if [[ -n "$untracked" ]]; then
        echo -e "\n[LOOP] Untracked files detected — auto-committing..."
        git add -A
        git commit -m "chore(loop): auto-commit untracked files after run" || true
        git push 2>/dev/null || true
    fi
}

# ANSI color codes
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_DIM='\033[2m'
C_GREEN='\033[32m'
C_YELLOW='\033[33m'

# Get color for tool name
get_tool_color() {
    case "$1" in
        Read)                echo '\033[36m' ;; # Cyan
        Edit)                echo '\033[33m' ;; # Yellow
        Write)               echo '\033[32m' ;; # Green
        Bash)                echo '\033[31m' ;; # Red
        Glob|Grep)           echo '\033[35m' ;; # Magenta
        Task)                echo '\033[34m' ;; # Blue
        Skill)               echo '\033[95m' ;; # Light Magenta
        WebSearch|WebFetch)  echo '\033[94m' ;; # Light Blue
        *)                   echo '\033[37m' ;; # White
    esac
}

# Format tool_use content block
format_tool_use() {
    local rest="${1#TOOL_USE|}"
    local name="${rest%%|*}"
    rest="${rest#*|}"
    local id="${rest%%|*}"
    local params="${rest#*|}"
    local color
    color=$(get_tool_color "$name")

    local ctx=""
    if [[ -n "$CTX_FILE" && -f "$CTX_FILE" ]]; then
        local tokens
        tokens=$(cat "$CTX_FILE" 2>/dev/null || echo 0)
        [[ "$tokens" -gt 0 ]] && ctx="${C_DIM} | Ctx: $((tokens * 100 / CONTEXT_WINDOW))%"
    fi

    echo -e "\n${C_BOLD}${color}[${SCRIPT_NAME^}] Tool Use: ${name}${ctx}${C_RESET}"
    echo -e "${C_DIM}Tool ID: ${id}${C_RESET}"
    echo "$params" | jq -C . 2>/dev/null || echo -e "${C_YELLOW}${params}${C_RESET}"
}

# jq filter: sum input tokens from a usage object
JQ_SUM_TOKENS='(.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0) | select(. > 0)'

# Format JSON stream from Claude CLI into readable console output
format_stream() {
    while IFS= read -r line; do
        local msg_type
        msg_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)

        case "$msg_type" in
            assistant)
                if [[ -n "$CTX_FILE" ]]; then
                    local is_subagent
                    is_subagent=$(echo "$line" | jq -r '.parent_tool_use_id // empty' 2>/dev/null)
                    if [[ -z "$is_subagent" ]]; then
                        local atokens
                        atokens=$(echo "$line" | jq -r "if .message.usage then .message.usage | $JQ_SUM_TOKENS else empty end" 2>/dev/null)
                        [[ -n "$atokens" ]] && echo "$atokens" > "$CTX_FILE"
                    fi
                fi
                echo "$line" | jq -r '
                    .message.content[]? |
                    if .type == "text" then "TEXT|\(.text | select(. != "" and . != null))"
                    elif .type == "tool_use" then "TOOL_USE|\(.name)|\(.id)|\(.input | tojson)"
                    else empty end
                ' 2>/dev/null | while IFS= read -r content; do
                    case "$content" in
                        TEXT\|*)     echo -e "\n${content#TEXT|}" ;;
                        TOOL_USE\|*) format_tool_use "$content" ;;
                    esac
                done
                ;;
            result)
                if [[ -n "$CTX_FILE" ]]; then
                    local rtokens
                    rtokens=$(echo "$line" | jq -r "if .usage then .usage | $JQ_SUM_TOKENS else empty end" 2>/dev/null)
                    [[ -n "$rtokens" ]] && echo "$rtokens" > "$CTX_FILE"
                fi
                local result
                result=$(echo "$line" | jq -r '.result // empty' 2>/dev/null)
                [[ -n "$result" ]] && echo -e "\n${C_GREEN}✓ Done: ${result:0:80}${C_RESET}"
                ;;
        esac
    done
}

# Resolve idea content from @file path, URL, or inline text
resolve_idea() {
    local idea="$1"

    # @file — read content from file
    if [[ "$idea" == @* ]]; then
        local file="${idea#@}"
        if [[ ! -f "$file" ]]; then
            echo "[WARN] Idea file not found: $file" >&2
            return 1
        fi
        cat "$file"
        return 0
    fi

    # GitHub issue or PR URL — use gh CLI
    if [[ "$idea" =~ ^https?://github\.com/[^/]+/[^/]+/(issues|pull)/[0-9]+ ]]; then
        if ! command -v gh &>/dev/null; then
            echo "[WARN] gh CLI not found, cannot fetch GitHub content" >&2
            return 1
        fi
        local gh_type
        case "${BASH_REMATCH[1]}" in
            issues) gh_type="issue" ;;
            pull)   gh_type="pr" ;;
        esac
        local body
        body=$(gh "$gh_type" view "$idea" --json body -q .body 2>/dev/null)
        if [[ $? -ne 0 || -z "$body" ]]; then
            echo "[WARN] Failed to fetch GitHub $gh_type: $idea" >&2
            return 1
        fi
        echo "$body"
        return 0
    fi

    # Generic URL — use curl
    if [[ "$idea" =~ ^https?:// ]]; then
        if ! command -v curl &>/dev/null; then
            echo "[WARN] curl not found, cannot fetch URL" >&2
            return 1
        fi
        local content
        content=$(curl -sL --max-time 10 "$idea" 2>/dev/null)
        if [[ $? -ne 0 || -z "$content" ]]; then
            echo "[WARN] Failed to fetch URL: $idea" >&2
            return 1
        fi
        echo "$content" | sed -e 's/<[^>]*>//g' -e '/^[[:space:]]*$/d' | head -200
        return 0
    fi

    # Inline text — return as-is
    echo "$idea"
}

# Write idea to docs/IDEA.md if provided
write_idea() {
    [[ -z "$IDEA" ]] && return

    local content
    content=$(resolve_idea "$IDEA")
    if [[ $? -ne 0 ]]; then
        echo "[WARN] Could not resolve idea, skipping IDEA write" >&2
        return 1
    fi

    mkdir -p docs
    cat > docs/IDEA.md << 'IDEA_EOF'
# Idea

IDEA_EOF
    echo "$content" >> docs/IDEA.md
    echo "Idea written to: docs/IDEA.md"
}

# Pre-process long options
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --idea) IDEA="$2"; shift 2 ;;
        --help) usage ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
set -- "${ARGS[@]}"

# Parse arguments
while getopts "danhi:" opt; do
    case $opt in
        d) SCRIPT_NAME="design" ;;
        a) AUTONOMOUS=true ;;
        n) NEW_CYCLE=true ;;
        i) IDEA=$OPTARG ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Design mode is always interactive
if [[ "$SCRIPT_NAME" == "design" ]]; then
    AUTONOMOUS=false
fi

# Select prompt file — use project-local symlink if available, else built-in
if [[ -f "loop/PROMPT_${SCRIPT_NAME}.md" ]]; then
    PROMPT_FILE="loop/PROMPT_${SCRIPT_NAME}.md"
else
    PROMPT_FILE="$LOOP_ROOT/prompts/PROMPT_${SCRIPT_NAME}.md"
fi

# Archive completed plan if --new flag set
if [[ "$NEW_CYCLE" == true ]]; then
    archive_completed_plan
fi

# Write idea file if provided
write_idea

# Print configuration
echo "Mode: $SCRIPT_NAME"
[[ "$AUTONOMOUS" == true ]] && echo "Autonomous mode"
[[ -n "$IDEA" ]] && echo "Idea: $IDEA"

if [[ "$AUTONOMOUS" == true ]]; then
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_$(date +%Y%m%d_%H%M%S).jsonl"
    CTX_FILE="$LOG_DIR/.ctx_tokens"
    echo "0" > "$CTX_FILE"
    echo "Log file: $LOG_FILE"

    claude -p --verbose --output-format stream-json --disallowedTools "AskUserQuestion" < "$PROMPT_FILE" \
        | tee -a "$LOG_FILE" | format_stream

    ensure_committed
    EXIT_STATUS="completed"
    echo -e "\nCompleted"
    echo "Logs saved to: $LOG_FILE"
else
    # Design mode: single interactive session
    claude < "$PROMPT_FILE"
    ensure_committed
fi
