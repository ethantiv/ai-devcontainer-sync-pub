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

# Tracking variables for notifications
START_TIME=$(date +%s)
COMPLETED_ITERATIONS=0
EXIT_STATUS="interrupted"

# Cleanup function - called on exit
cleanup() {
    local duration=$(($(date +%s) - START_TIME))

    # Generate run summary to file (best-effort, uses Node.js JSONL parser)
    node -e "require('$LOOP_ROOT/lib/summary').generateSummary('$LOG_DIR').then(s => process.stdout.write(s))" \
        > "$LOG_DIR/summary-latest.txt" 2>/dev/null || true

    echo ""
    echo "[CLEANUP] Cleaning up background processes..."
    "$LOOP_SCRIPTS_DIR/cleanup.sh" 2>/dev/null || true
}

# Trap handlers - defense in depth (layer 1)
trap cleanup EXIT SIGINT SIGTERM SIGHUP

# Default values
ITERATIONS=""
AUTONOMOUS=false
LOG_DIR="loop/logs"
SCRIPT_NAME="build"
EARLY_EXIT=true
IDEA=""
CONTEXT_WINDOW=200000
CTX_FILE=""

# Help function
usage() {
    echo "Usage: $0 [-p] [-a] [-i iterations] [-e] [-I idea]"
    echo ""
    echo "Options:"
    echo "  -p              Plan mode (default: build)"
    echo "  -a              Autonomous mode (default: interactive)"
    echo "  -i iterations   Number of iterations (default: 10 build, 5 plan)"
    echo "  -e              Disable early exit (run all iterations)"
    echo "  -I text         Seed idea written to docs/ROADMAP.md"
    echo "  -h              Show this help"
    echo ""
    echo "Note: When called via 'loop run', autonomous mode (-a) is the default."
    echo ""
    echo "Examples:"
    echo "  $0 -a              Build, 10 autonomous iterations"
    echo "  $0 -p -a           Plan, 5 autonomous iterations"
    echo "  $0 -p -a -i 1     Single planning iteration"
    echo "  $0 -a -e           Build, all iterations (no early exit)"
    exit 0
}

# Check if plan is complete (no unchecked tasks and has completion marker)
check_completion() {
    local plan="docs/plans/IMPLEMENTATION_PLAN.md"
    [[ ! -f "$plan" ]] && return 1

    local incomplete complete_marker
    incomplete=$(grep -cE '^[[:space:]]*-[[:space:]]*\[[[:space:]]\]' "$plan" 2>/dev/null) || incomplete=0
    complete_marker=$(grep -cE '\*{0,2}Status\*{0,2}:\*{0,2}\s*(COMPLETE|DONE)|BUILD COMPLETE|PLAN COMPLETE' "$plan" 2>/dev/null) || complete_marker=0

    [[ "$incomplete" -eq 0 && "$complete_marker" -gt 0 ]]
}

# Post-iteration git safety net — auto-commit if agent skipped git
ensure_committed() {
    git rev-parse --is-inside-work-tree &>/dev/null || return 0
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        echo -e "\n[LOOP] Uncommitted changes detected after iteration — auto-committing..."
        git add -A
        git commit -m "chore(loop): auto-commit after iteration (agent skipped commit)" || true
        git push 2>/dev/null || true
    fi
    local untracked
    untracked=$(git ls-files --others --exclude-standard 2>/dev/null | head -1)
    if [[ -n "$untracked" ]]; then
        echo -e "\n[LOOP] Untracked files detected after iteration — auto-committing..."
        git add -A
        git commit -m "chore(loop): auto-commit untracked files after iteration" || true
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

    echo -e "\n${C_BOLD}${color}[${SCRIPT_NAME^}-${i}] Tool Use: ${name}${ctx}${C_RESET}"
    echo -e "${C_DIM}Tool ID: ${id}${C_RESET}"
    echo "$params" | jq -C . 2>/dev/null || echo -e "${C_YELLOW}${params}${C_RESET}"
}

# Format JSON stream from Claude CLI into readable console output
format_stream() {
    while IFS= read -r line; do
        local msg_type
        msg_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)

        case "$msg_type" in
            assistant)
                if [[ -n "$CTX_FILE" ]]; then
                    local atokens
                    atokens=$(echo "$line" | jq -r '
                        if .message.usage then
                            (.message.usage.input_tokens // 0) +
                            (.message.usage.cache_read_input_tokens // 0) +
                            (.message.usage.cache_creation_input_tokens // 0)
                        else empty end | select(. > 0)
                    ' 2>/dev/null)
                    if [[ -n "$atokens" ]]; then
                        local prev
                        prev=$(cat "$CTX_FILE" 2>/dev/null || echo 0)
                        [[ "$atokens" -gt "$prev" ]] && echo "$atokens" > "$CTX_FILE"
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
                    rtokens=$(echo "$line" | jq -r '
                        if .usage then
                            (.usage.input_tokens // 0) +
                            (.usage.cache_read_input_tokens // 0) +
                            (.usage.cache_creation_input_tokens // 0)
                        else empty end | select(. > 0)
                    ' 2>/dev/null)
                    if [[ -n "$rtokens" ]]; then
                        local prev
                        prev=$(cat "$CTX_FILE" 2>/dev/null || echo 0)
                        [[ "$rtokens" -gt "$prev" ]] && echo "$rtokens" > "$CTX_FILE"
                    fi
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

    # GitHub issue URL — use gh issue view
    if [[ "$idea" =~ ^https?://github\.com/[^/]+/[^/]+/issues/[0-9]+ ]]; then
        if ! command -v gh &>/dev/null; then
            echo "[WARN] gh CLI not found, cannot fetch GitHub issue" >&2
            return 1
        fi
        local body
        body=$(gh issue view "$idea" --json body -q .body 2>/dev/null)
        if [[ $? -ne 0 || -z "$body" ]]; then
            echo "[WARN] Failed to fetch GitHub issue: $idea" >&2
            return 1
        fi
        echo "$body"
        return 0
    fi

    # GitHub PR URL — use gh pr view
    if [[ "$idea" =~ ^https?://github\.com/[^/]+/[^/]+/pull/[0-9]+ ]]; then
        if ! command -v gh &>/dev/null; then
            echo "[WARN] gh CLI not found, cannot fetch GitHub PR" >&2
            return 1
        fi
        local body
        body=$(gh pr view "$idea" --json body -q .body 2>/dev/null)
        if [[ $? -ne 0 || -z "$body" ]]; then
            echo "[WARN] Failed to fetch GitHub PR: $idea" >&2
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
        # Strip HTML tags for basic content extraction
        echo "$content" | sed 's/<[^>]*>//g' | sed '/^[[:space:]]*$/d' | head -200
        return 0
    fi

    # Inline text — return as-is
    echo "$idea"
}

# Write idea to docs/ROADMAP.md if provided
write_idea() {
    [[ -z "$IDEA" ]] && return

    local content
    content=$(resolve_idea "$IDEA")
    if [[ $? -ne 0 ]]; then
        echo "[WARN] Could not resolve idea, skipping ROADMAP write" >&2
        return 1
    fi

    mkdir -p docs
    cat > docs/ROADMAP.md << 'IDEA_EOF'
# Roadmap

IDEA_EOF
    echo "$content" >> docs/ROADMAP.md
    echo "Idea written to: docs/ROADMAP.md"
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
while getopts "pai:ehI:" opt; do
    case $opt in
        p) SCRIPT_NAME="plan" ;;
        a) AUTONOMOUS=true ;;
        i) ITERATIONS=$OPTARG ;;
        e) EARLY_EXIT=false ;;
        I) IDEA=$OPTARG ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Default iterations: 5 for plan, 10 for build
if [[ -z "$ITERATIONS" ]]; then
    if [[ "$SCRIPT_NAME" == "plan" ]]; then
        ITERATIONS=5
    else
        ITERATIONS=10
    fi
fi

# Select prompt file — use project-local symlink if available, else built-in
if [[ -f "loop/PROMPT_${SCRIPT_NAME}.md" ]]; then
    PROMPT_FILE="loop/PROMPT_${SCRIPT_NAME}.md"
else
    PROMPT_FILE="$LOOP_ROOT/prompts/PROMPT_${SCRIPT_NAME}.md"
fi

# Write idea file if provided
write_idea

# Check if early exit conditions are met (skip for plan mode)
should_exit_early() {
    [[ "$EARLY_EXIT" == true && "$SCRIPT_NAME" != "plan" ]] && check_completion
}

# Print configuration
print_config() {
    echo "Mode: $SCRIPT_NAME${1:+ ($1)}"
    [[ "$AUTONOMOUS" == true ]] && echo "Autonomous mode: $ITERATIONS iterations"
    [[ "$AUTONOMOUS" == true && "$SCRIPT_NAME" != "plan" ]] && echo "Early exit: $EARLY_EXIT"
    [[ -n "$IDEA" ]] && echo "Idea: $IDEA"
}

if [[ "$AUTONOMOUS" == true ]]; then
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_$(date +%Y%m%d_%H%M%S).jsonl"
    CTX_FILE="$LOG_DIR/.ctx_tokens"
    echo "0" > "$CTX_FILE"

    print_config
    echo "Log file: $LOG_FILE"

    for ((i=1; i<=ITERATIONS; i++)); do
        if should_exit_early; then
            echo -e "\n[EARLY EXIT] Plan 100% complete before iteration $i."
            EXIT_STATUS="success"
            break
        fi

        echo -e "\n=============================\n  Iteration $i/$ITERATIONS\n============================="
        echo "$i" > "$LOG_DIR/.progress"

        claude -p --verbose --output-format stream-json < "$PROMPT_FILE" | tee -a "$LOG_FILE" | format_stream
        ((COMPLETED_ITERATIONS++))
        ensure_committed

        [[ $i -lt $ITERATIONS ]] && sleep 10
    done

    [[ "$EXIT_STATUS" == "interrupted" ]] && EXIT_STATUS="completed"

    echo -e "\nCompleted iterations (may have exited early)"
    echo "Logs saved to: $LOG_FILE"
else
    print_config "interactive"

    while :; do
        if should_exit_early; then
            echo "[EARLY EXIT] Plan 100% complete."
            EXIT_STATUS="success"
            break
        fi

        clear
        claude < "$PROMPT_FILE"
        ((COMPLETED_ITERATIONS++))
        ensure_committed
        sleep 10
    done
fi
