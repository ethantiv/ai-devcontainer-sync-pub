#!/bin/bash

# Autonomous development loop powered by Claude CLI
# Part of ai-devcontainer-sync

# Resolve script directory (works with symlinks)
LOOP_SCRIPTS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LOOP_ROOT="$(dirname "$LOOP_SCRIPTS_DIR")"

# Tracking variables for notifications
START_TIME=$(date +%s)
COMPLETED_ITERATIONS=0
EXIT_STATUS="interrupted"

# Cleanup function - called on exit
cleanup() {
    local duration=$(($(date +%s) - START_TIME))

    # Send Telegram notification
    "$LOOP_SCRIPTS_DIR/notify-telegram.sh" \
        --mode "$SCRIPT_NAME" \
        --iterations "$COMPLETED_ITERATIONS" \
        --total "$ITERATIONS" \
        --duration "$duration" \
        --status "$EXIT_STATUS"

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

# Help function
usage() {
    echo "Usage: $0 [-p] [-a] [-i iterations] [-e] [-I idea]"
    echo ""
    echo "Options:"
    echo "  -p              Plan mode (default: build)"
    echo "  -a              Autonomous mode (default: interactive)"
    echo "  -i iterations   Number of iterations (default: 5 build, 3 plan)"
    echo "  -e              Disable early exit (run all iterations)"
    echo "  -I text         Seed idea written to docs/IDEA.md"
    echo "  -h              Show this help"
    echo ""
    echo "Note: When called via 'loop run', autonomous mode (-a) is the default."
    echo ""
    echo "Examples:"
    echo "  $0 -a              Build, 5 autonomous iterations"
    echo "  $0 -p -a           Plan, 3 autonomous iterations"
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

    echo -e "\n${C_BOLD}${color}Tool Use: ${name}${C_RESET}"
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
                local result
                result=$(echo "$line" | jq -r '.result // empty' 2>/dev/null)
                [[ -n "$result" ]] && echo -e "\n${C_GREEN}✅ Done: ${result:0:80}${C_RESET}"
                ;;
        esac
    done
}

# Write idea to docs/IDEA.md if provided
write_idea() {
    [[ -z "$IDEA" ]] && return

    mkdir -p docs
    cat > docs/IDEA.md << EOF
# User Idea

$IDEA
EOF
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

# Default iterations: 3 for plan, 5 for build
if [[ -z "$ITERATIONS" ]]; then
    if [[ "$SCRIPT_NAME" == "plan" ]]; then
        ITERATIONS=3
    else
        ITERATIONS=5
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
    [[ "$AUTONOMOUS" == true ]] && echo "Early exit: $EARLY_EXIT"
    [[ -n "$IDEA" ]] && echo "Idea: $IDEA"
}

if [[ "$AUTONOMOUS" == true ]]; then
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_$(date +%Y%m%d_%H%M%S).jsonl"

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
        sleep 10
    done
fi
