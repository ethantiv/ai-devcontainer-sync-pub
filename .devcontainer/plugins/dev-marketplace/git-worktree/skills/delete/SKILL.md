---
name: git-worktree:delete
description: >
  This skill should be used when the user asks to "delete a git worktree",
  "remove worktree", "git worktree delete", "git worktree remove",
  "clean up worktree", or mentions deleting, removing, or cleaning up
  a git worktree and its associated branch.
---

Delete an existing Git worktree and its associated branch.

Follow these steps precisely:

1. Get the project name by running `basename "$(git rev-parse --show-toplevel)"` to extract the repository directory name.

2. Ask the user for the worktree name if not provided in their message.

3. Determine the worktree directory path: `$(git rev-parse --show-toplevel)/../{project}-{name}` where `{project}` is the repo directory name and `{name}` is the provided name.

4. Verify the worktree exists by running `git worktree list` and checking for the path. If it does not exist, inform the user and stop.

5. Remove the worktree by running `git worktree remove {path}`.

6. Delete the associated branch by running `git branch -d {name}`. If it fails because the branch has unmerged changes, inform the user and ask whether to force-delete with `git branch -D {name}`.

7. After successful deletion, output a summary:
   - Removed worktree path
   - Deleted branch name
