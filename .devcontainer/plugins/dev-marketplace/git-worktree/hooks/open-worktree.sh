#!/usr/bin/env bash
# PostToolUse hook: open new git worktree in VS Code after creation

set -euo pipefail

input=$(cat)

command=$(echo "$input" | jq -r '.tool_input.command // empty')

if [[ -z "$command" ]]; then
  exit 0
fi

if ! echo "$command" | grep -q 'git worktree add'; then
  exit 0
fi

# Extract worktree path from: git worktree add [-b branch] <path> [<commit-ish>]
# Remove everything up to and including "git worktree add "
args=$(echo "$command" | sed -E 's/.*git worktree add //')

# Skip -b <branch> flag if present
args=$(echo "$args" | sed -E 's/^-b\s+\S+\s*//')

# First remaining argument is the path
worktree_path=$(echo "$args" | awk '{print $1}')

if [[ -n "$worktree_path" && -d "$worktree_path" ]]; then
  code "$worktree_path" &
fi

exit 0
