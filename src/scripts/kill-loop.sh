#!/bin/bash
# Kill all running loop.sh processes and their children (claude -p, MCP servers, etc.)

KILLED=0

for pid in $(pgrep -f 'loop\.sh'); do
    # Skip this script
    [[ "$pid" == "$$" ]] && continue

    echo "Killing loop.sh (PID $pid) and children..."
    pkill -KILL -P "$pid" 2>/dev/null
    kill -KILL "$pid" 2>/dev/null
    ((KILLED++))
done

# Catch any orphaned claude -p processes from the loop
for pid in $(pgrep -f 'claude.*-p.*--output-format'); do
    echo "Killing orphaned claude -p (PID $pid)..."
    kill -KILL "$pid" 2>/dev/null
    ((KILLED++))
done

if [[ "$KILLED" -eq 0 ]]; then
    echo "No loop processes found."
else
    echo "Done. Killed $KILLED process(es)."
fi
