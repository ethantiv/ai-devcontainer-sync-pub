#!/bin/bash
# Cleanup dev server ports without pkill/ps (sandbox-compatible)
# Uses fuser -k which is available in sandbox

PORTS=(${LOOP_PORTS:-3000 3001 5173 5174 8080 8081 4173})

for port in "${PORTS[@]}"; do
    if lsof -i :"$port" >/dev/null 2>&1; then
        fuser -k "$port/tcp" 2>/dev/null || true
        echo "Released port $port"
    fi
done
