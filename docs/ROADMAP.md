# Roadmap

## Proposals

### P1 - Critical

#### Bot UI for project creation flow (Phase 3 of project creation feature)
Backend functions `validate_project_name()`, `create_project()`, and `create_github_repo()` are implemented with 16 MSG_* constants ready in `messages.py`, but the Telegram bot UI (Phase 3) was never built. Add conversation states in `bot.py` for: "Create project" button on project list, project name input with validation feedback, optional GitHub repo creation confirmation, and success/failure result with navigation back to project menu. This completes the project creation feature started in Phase 1+2+4.

### P2 - Important

#### Reduce bot.py size by extracting handler modules
`bot.py` is 1,723 lines — the largest file in the codebase — mixing conversation handlers, callback queries, keyboard builders, and state management. Extract logically grouped handlers into separate modules (e.g. `handlers/projects.py`, `handlers/brainstorm.py`, `handlers/queue.py`) while keeping `bot.py` as the thin wiring layer that registers handlers with the Application. This improves readability and makes parallel development easier.

### P3 - Nice to Have

#### Pagination for project list in Telegram
`list_projects()` renders all projects as inline keyboard buttons in a single message. With 10+ projects the button list becomes unwieldy on mobile. Add pagination (5 projects per page) with "Next/Previous" navigation buttons, preserving the existing "Create project" and "Clone repo" buttons on every page.
