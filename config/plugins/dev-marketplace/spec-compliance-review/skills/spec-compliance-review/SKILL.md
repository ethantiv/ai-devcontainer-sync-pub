---
name: spec-compliance-review
description: This skill should be used when the user asks to "check spec compliance", "review plan against spec", "verify implementation matches specification", "compare spec with plan", "find gaps between spec and implementation", "sprawdź zgodność ze specyfikacją", "porównaj plan ze specem", or mentions auditing whether a plan, code, or PR covers every requirement of a design document. Triggers on requests to find missing, deviated, or incomplete elements between a specification and its implementation artifact.
argument-hint: <spec-path> <target-path> [additional-target-paths...]
user-invocable: true
---

# Spec Compliance Review

Systematically verify that a target artifact (implementation plan, code changes, PR, or commit range) covers every requirement of a specification document. Produce a structured gap report classified by severity.

## Inputs

Arguments passed by the user:
- `$1` — path to the specification document (optional; auto-discovered if omitted — see below)
- `$2..$N` — paths to target artifacts to verify against the spec (required, at least one)

Target artifacts may be:
- A single plan document (e.g. `docs/plans/feature.md`)
- A directory of source files
- A list of files
- A git ref range (if argument matches `^[a-f0-9]+\.\.[a-f0-9]+$` or contains `..`)

### Auto-discovery of the specification

If `$1` is not provided, resolve the spec in this order **before** asking the user:

1. **`docs/superpowers/specs/*.md`** — Glob for markdown files in this directory.
   - Exactly one match → use it as the spec.
   - Multiple matches → list them to the user and ask which one to use.
   - No matches → fall through to step 2.
2. **`docs/IDEA.md`** — if it exists, use it as the spec (the seed document for `loop design` / `loop run`).
3. Neither location yielded a file → ask the user to provide the spec path explicitly.

Why this order: in projects that use the superpowers/loop workflow, `docs/superpowers/specs/` is the canonical home for formal specifications produced by the `writing-plans` and related skills. `docs/IDEA.md` is the earlier, lighter-weight seed document and should only be used when no formal spec has been written yet.

If `$2` (target) is missing, always ask the user — target artifacts are not auto-discovered.

## Workflow

Create a TodoWrite list with these five phases and mark each in_progress/completed as you execute.

### Phase 1: Read the specification

Read the full spec file. If it exceeds 2000 lines, read in chunks.

Extract a **checklist of concrete requirements** by scanning for:
- Files to create, modify, or remove (usually in tables or explicit lists)
- Named functions, classes, CLI flags, parameters, environment variables
- Configuration changes (Dockerfile, package.json, schema, env vars)
- Behavioral requirements ("must", "should", "MUST", numbered lists, workflow steps)
- Error-handling and edge-case requirements
- Testing requirements (unit tests, integration tests, fixtures)
- Versioning / migration / cleanup requirements
- Explicit out-of-scope statements (track these separately — they are NOT gaps)

Produce an internal enumerated list. Aim for one requirement per atomic verifiable claim. A spec table with 8 rows produces ~8 items, not 1.

### Phase 2: Read the target artifact(s)

For each target path:
- If it is a single document → Read fully
- If it is a directory → Glob for relevant files (`*.md`, `*.ts`, `*.js`, etc.), then Read each
- If it is a git ref range → `git diff <range> --stat` then `git log <range>` to get change summary, then `git show <commit>` for each relevant commit
- If it is a list of files → Read each

Build an internal map of what the target actually does/produces.

### Phase 3: Systematic comparison

For EVERY item in the Phase 1 checklist, determine its status:

| Status | Meaning |
|---|---|
| ✅ Covered | Target implements or explicitly addresses the requirement |
| ⚠️ Partial | Target addresses part but misses a sub-requirement (e.g. flag missing, test case missing, value mismatch) |
| ❌ Missing | Target does not address the requirement at all |
| 🔀 Deviated | Target does something different from what the spec prescribes (may or may not be acceptable) |
| ➖ Out of scope | Spec explicitly excludes this — include for completeness only |

**Critical discipline:** do NOT rationalize gaps away. If the spec says "CLI flag `--foo`" and the target implements `--bar`, that is a 🔀 Deviated, not ✅ Covered. If the spec lists three sub-items and target has two, that is ⚠️ Partial, not ✅. Be strict; the user relies on you catching what they missed.

Verify concrete claims with Grep/Read when possible. Example: if the spec says "add `VALIDATOR_SCRIPT_PATH` env var to Dockerfile", actually grep the Dockerfile for that string — do not infer from prose.

### Phase 4: Assign severity

For each non-✅ item, assign severity:

- **Critical** — breaks the feature, blocks deployment, or contradicts spec intent
- **Important** — feature works but a spec contract is broken (missing flag, wrong file path, missing error handling)
- **Minor** — deviation without functional impact (naming, minor structural difference, extra constraint)

### Phase 5: Present the report

Output the report in this exact structure, in the user's conversation language:

```
## Coverage summary

- Covered: X / N
- Partial: X
- Missing: X
- Deviated: X
- Out of scope: X

## Gaps (ordered by severity)

### Critical
1. **<spec item>** — <what target does/doesn't do> (spec: <file>:<section>, target: <file>:<line/section>)
2. ...

### Important
...

### Minor
...

## Fully covered (abbreviated)

- ✅ <item 1>
- ✅ <item 2>
- ... (collapse if >10)

## Recommendation

<2-4 sentences: what to fix first, which gaps block go/no-go, suggested patch order>
```

Always cite file paths with line numbers or section anchors so the user can jump directly to the source.

## Principles

- **Enumerate atomically.** One requirement per bullet. A table row with 5 columns about 5 different files = 5 items.
- **Verify, don't infer.** Grep for exact strings, flags, function names. Prose summary is not proof.
- **Be strict.** "Close enough" is a 🔀 Deviated, not ✅ Covered. Let the user decide if the deviation is acceptable.
- **Cite sources.** Every finding must reference spec location and target location.
- **Respect out-of-scope.** Spec's "Out of scope" sections are NOT gaps — list them only for completeness.
- **Report what matters first.** Critical gaps at the top. Minor nits at the bottom. Don't bury the lede.
- **No false reassurance.** If the target is fundamentally off-spec, say so in the recommendation. Do not pad with "but the overall direction is good" unless it is materially useful.

## What NOT to do

- Do not rewrite or fix the target — review only. The user invokes a different workflow to fix gaps.
- Do not editorialize about spec quality ("the spec is unclear here") unless genuinely blocking. Focus on coverage.
- Do not skip items because they seem obvious. Obvious items are exactly where regressions hide.
- Do not batch-mark items as ✅ without individual verification.
- Do not stop at the first critical gap — produce the full report so the user sees the whole picture.
