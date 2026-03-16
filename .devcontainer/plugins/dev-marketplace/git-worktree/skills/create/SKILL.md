---
name: git-worktree:create
description: >
  This skill should be used when the user asks to "create a git worktree",
  "new worktree", "git worktree create", "add worktree", "git worktree add",
  "create a new branch worktree", or mentions creating, adding, or setting up
  a git worktree for parallel development.
---

Create a new Git worktree based on the provided name.

Follow these steps precisely:

1. Get the project name by running `basename "$(git rev-parse --show-toplevel)"` to extract the repository directory name.

2. Ask the user for the worktree name if not provided in their message.

3. Determine the worktree directory path: `$(git rev-parse --show-toplevel)/../{project}-{name}` where `{project}` is the repo directory name and `{name}` is the provided name.

4. Check if a branch named `{name}` already exists by running `git branch --list {name}`.
   - If the branch exists: create the worktree using `git worktree add {path} {name}`
   - If the branch does NOT exist: create the worktree with a new branch using `git worktree add -b {name} {path}`

5. After successful creation, output a summary:
   - Worktree path
   - Branch name
   - Open: `code {path}` to open the new worktree
