---
allowed-tools: Bash(git worktree:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(basename:*)
description: Create a new git worktree with naming convention {project}-{name} on branch {name}
argument-hint: <name>
---

Create a new Git worktree based on the provided name argument.

Follow these steps precisely:

1. Get the project name by running `basename "$(git rev-parse --show-toplevel)"` to extract the repository directory name.

2. Parse the name argument from: $ARGUMENTS. If no argument is provided, stop and ask the user for a worktree name.

3. Determine the worktree directory path: `$(git rev-parse --show-toplevel)/../{project}-{name}` where `{project}` is the repo directory name and `{name}` is the argument.

4. Check if a branch named `{name}` already exists by running `git branch --list {name}`.
   - If the branch exists: create the worktree using `git worktree add {path} {name}`
   - If the branch does NOT exist: create the worktree with a new branch using `git worktree add -b {name} {path}`

5. After successful creation, output a summary:
   - Worktree path
   - Branch name
   - Hint: `cd {path}` to switch to the new worktree
