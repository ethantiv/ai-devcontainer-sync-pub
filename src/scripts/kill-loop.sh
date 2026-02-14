#!/bin/bash
# Kill all running loop.sh processes, their Node.js parents (loop run), children,
# orphaned claude -p processes, and Telegram bot tmux sessions.

KILLED=0

# Step 1: Find Node.js parent processes (loop run) to prevent build phase from spawning
declare -A NODE_PIDS
for pid in $(pgrep -f 'loop\.sh'); do
    [[ "$pid" == "$$" ]] && continue
    ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    [[ -z "$ppid" ]] && continue
    # Check if parent is a node process (the loop run CLI)
    if ps -o comm= -p "$ppid" 2>/dev/null | grep -q '^node'; then
        NODE_PIDS["$ppid"]=1
    fi
done

for npid in "${!NODE_PIDS[@]}"; do
    echo "Killing Node.js parent (PID $npid)..."
    kill -KILL "$npid" 2>/dev/null
    ((KILLED++))
done

# Step 2: Kill loop.sh processes and their children
for pid in $(pgrep -f 'loop\.sh'); do
    [[ "$pid" == "$$" ]] && continue

    echo "Killing loop.sh (PID $pid) and children..."
    pkill -KILL -P "$pid" 2>/dev/null
    kill -KILL "$pid" 2>/dev/null
    ((KILLED++))
done

# Step 3: Catch any orphaned claude -p processes from the loop
for pid in $(pgrep -f 'claude.*-p.*--output-format'); do
    echo "Killing orphaned claude -p (PID $pid)..."
    kill -KILL "$pid" 2>/dev/null
    ((KILLED++))
done

# Step 4: Kill Telegram bot tmux sessions matching loop-*
for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^loop-'); do
    echo "Killing tmux session '$session'..."
    tmux kill-session -t "$session" 2>/dev/null
    ((KILLED++))
done

if [[ "$KILLED" -eq 0 ]]; then
    echo "No loop processes found."
else
    echo "Done. Killed $KILLED process(es)."
fi
