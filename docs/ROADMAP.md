# Roadmap

## Proposals

### P2 - Important

#### Telegram bot: task history and log viewing
Currently the bot shows only live task status. Users have no way to review results of completed tasks, view build logs, or see what changed after a loop run finished. Add a "History" button to the project menu that lists recent tasks with their outcome (success/fail/iterations used), and allow viewing a summary of the last log file directly in Telegram. This would make the bot a complete remote control — not just for launching tasks but also for reviewing their results.

#### Loop: idea seeding from file and URL sources
`loop plan -I "text"` accepts inline ideas, but real-world planning often starts from a GitHub issue, a Confluence page, or a local design doc. Add support for `loop plan -I @file.md` (read idea from file) and `loop plan -I https://github.com/...` (fetch issue/PR body as idea seed). This removes the friction of manually copying context into the CLI and enables automation pipelines (e.g., Telegram bot forwarding a GitHub issue URL directly to a plan run).

#### Brainstorm session export and continuation
Brainstorm sessions are stored in `.brainstorm_state.json` but cannot be exported or resumed after the bot restarts. Add a `/brainstorming export` command that saves the full conversation as a Markdown file in `docs/brainstorms/`, and allow resuming the last session with `/brainstorming continue`. This preserves valuable design discussions that currently vanish when the container restarts.

#### Docker ARM build optimization
Full multi-stage build takes ~6 minutes on Raspberry Pi due to Playwright + Chromium installation during image build. Move Playwright browser installation to a lazy first-use pattern: skip `npx playwright install chromium` in the Dockerfile, and instead trigger it on the first `agent-browser` skill invocation. This cuts image build time in half for users who don't use browser automation, while keeping the same experience for those who do.

### P3 - Nice to Have

#### Loop workflow integration tests
Unit tests cover individual components well (438 Python + 20 JS), but there are no end-to-end tests for the full loop workflow: init a project, run a plan iteration, verify output artifacts. Add a small integration test suite (pytest + subprocess) that exercises `loop init`, validates symlink creation, runs `loop plan -i 1` against a mock project, and checks that `IMPLEMENTATION_PLAN.md` and log files are produced correctly.

#### Telegram bot handler state machine diagram
The ConversationHandler has 9 states with branching transitions across 5 handler modules. Add a Mermaid state diagram to `src/telegram_bot/COMMANDS.md` showing the full flow: SELECT_PROJECT to PROJECT_MENU to each sub-flow (task, brainstorm, clone, create, worktree). This helps new contributors understand the bot's conversation logic without reading all handler code.
