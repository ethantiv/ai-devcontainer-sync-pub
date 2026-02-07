## Build & Run

<!-- Succinct rules for how to BUILD the project -->

## Validation

<!-- Run these after implementing to get immediate feedback -->

- Tests: `[test command]`
- Typecheck: `[typecheck command]`
- Lint: `[lint command]`

### Test Output Guidelines

- Keep test stdout minimal: summary line with pass/fail counts
- Pipe full output to `loop/logs/test-output.log` (e.g., `npm test 2>&1 | tee loop/logs/test-output.log`)
- Use ERROR prefix on failure summary lines for grep: `ERROR: 3 tests failed out of 47`
- On failure, log 3-line diagnostic: which test, error message, root cause hypothesis

## Operational Notes

<!-- Succinct learnings about how to RUN the project -->

### Codebase Patterns

<!-- Document recurring patterns, conventions, and architectural decisions -->
