---
allowed-tools: Bash(git worktree:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(basename:*)
description: Delete a git worktree and its branch by name
argument-hint: <name>
---

Delete an existing Git worktree and its associated branch.

Follow these steps precisely:

1. Get the project name by running `basename "$(git rev-parse --show-toplevel)"` to extract the repository directory name.

2. Parse the name argument from: $ARGUMENTS. If no argument is provided, stop and ask the user for a worktree name.

3. Determine the worktree directory path: `$(git rev-parse --show-toplevel)/../{project}-{name}` where `{project}` is the repo directory name and `{name}` is the argument.

4. Verify the worktree exists by running `git worktree list` and checking for the path. If it does not exist, inform the user and stop.

5. Remove the worktree by running `git worktree remove {path}`.

6. Delete the associated branch by running `git branch -d {name}`. If it fails because the branch has unmerged changes, inform the user and ask whether to force-delete with `git branch -D {name}`.

7. After successful deletion, output a summary:
   - Removed worktree path
   - Deleted branch name
