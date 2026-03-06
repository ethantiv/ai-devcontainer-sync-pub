---
name: dependency-update
description: >
  This skill should be used when the user asks to "update dependencies",
  "upgrade packages", "check for outdated libraries", "update frameworks",
  "bump versions", "update npm packages", "upgrade pip packages",
  "update all dependencies to latest", "check outdated dependencies",
  or mentions updating, upgrading, or bumping project dependency versions.
---

# Dependency Update

Scan the current project for dependency manifests across all ecosystems, update dependencies to their latest versions, and verify the project still works after the update.

## Workflow

### Step 1: Discover Dependency Files

Scan the project root (and common subdirectories) for dependency manifests. Look for these files using the Glob tool:

| Ecosystem | Files to find |
|-----------|---------------|
| Node.js | `package.json` |
| Python | `requirements*.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile` |
| Ruby | `Gemfile` |
| Go | `go.mod` |
| Rust | `Cargo.toml` |
| PHP | `composer.json` |
| Java/Kotlin | `pom.xml`, `build.gradle`, `build.gradle.kts` |
| .NET | `*.csproj`, `*.fsproj`, `Directory.Packages.props` |
| Dart/Flutter | `pubspec.yaml` |
| Elixir | `mix.exs` |
| Swift | `Package.swift` |

Use a broad glob pattern like `**/{package.json,requirements*.txt,pyproject.toml,go.mod,Cargo.toml,composer.json,Gemfile,pom.xml,build.gradle,pubspec.yaml,mix.exs,Package.swift,*.csproj}` but exclude `node_modules/`, `vendor/`, `.venv/`, `target/`, `build/` directories.

Report findings to the user: which ecosystems were detected and which files found.

### Step 2: Check Currently Installed Versions

For each detected ecosystem, run the appropriate command to list outdated dependencies:

| Ecosystem | Command |
|-----------|---------|
| Node.js | `npm outdated` or `yarn outdated` or `pnpm outdated` (check lockfile to determine package manager) |
| Python (pip) | `pip list --outdated` |
| Python (pipenv) | `pipenv update --outdated` |
| Python (poetry) | `poetry show --outdated` |
| Ruby | `bundle outdated` |
| Go | `go list -m -u all` |
| Rust | `cargo install cargo-outdated 2>/dev/null; cargo outdated` |
| PHP | `composer outdated --direct` |
| Java (Maven) | `mvn versions:display-dependency-updates` |
| Java (Gradle) | `gradle dependencyUpdates` (if plugin available) |
| .NET | `dotnet list package --outdated` |
| Dart | `dart pub outdated` or `flutter pub outdated` |
| Elixir | `mix hex.outdated` |

Present a summary table of outdated dependencies with current vs latest versions.

### Step 3: Research Breaking Changes (if major bumps)

For any **major version bumps** (e.g., 2.x → 3.x), research breaking changes before updating:

1. **context7 MCP** — Use `resolve-library-id` then `query-docs` to find migration guides and changelogs for the library. Prefer this over web fetching.
2. **agent-browser** — If context7 lacks migration info, use the agent-browser skill to visit the library's changelog, release notes, or migration guide page on GitHub/docs site.

Summarize breaking changes and required code modifications for the user before proceeding.

### Step 4: Update Dependencies

Run the appropriate update commands for each ecosystem:

| Ecosystem | Update command |
|-----------|---------------|
| Node.js (npm) | `npm update` for semver-compatible, `npx npm-check-updates -u && npm install` for latest |
| Node.js (yarn) | `yarn upgrade` or `yarn up` (yarn 2+) |
| Node.js (pnpm) | `pnpm update --latest` |
| Python (pip) | `pip install --upgrade <package>` for each, or `pip-compile --upgrade` if using pip-tools |
| Python (poetry) | `poetry update` |
| Python (pipenv) | `pipenv update` |
| Ruby | `bundle update` |
| Go | `go get -u ./... && go mod tidy` |
| Rust | `cargo update` |
| PHP | `composer update` |
| Java (Maven) | Update version numbers in `pom.xml` manually |
| Java (Gradle) | Update version numbers in `build.gradle` manually |
| .NET | `dotnet outdated --upgrade` or update `*.csproj` manually |
| Dart | `dart pub upgrade --major-versions` or `flutter pub upgrade --major-versions` |
| Elixir | `mix deps.update --all` |

For ecosystems without a single "update all" command (Maven, Gradle), edit the manifest files directly using the Edit tool to bump version numbers.

### Step 5: Verify

After updating, run the project's validation suite. Check for:

1. **Lock file regenerated** — Confirm lockfile was updated (package-lock.json, yarn.lock, Pipfile.lock, etc.)
2. **Build passes** — Run the build command if applicable
3. **Tests pass** — Run the test suite defined in CLAUDE.md or detected from the project
4. **Type checking passes** — Run typecheck if applicable

If tests or build fail after update, investigate the failure:
- Read error messages carefully
- Check if it's related to a breaking change from a major bump
- Use context7 to look up the new API if something changed
- Fix compatibility issues in the codebase
- Re-run verification

### Step 6: Report

Present a final summary to the user:

```
## Dependency Update Summary

### Updated
| Package | From | To | Ecosystem |
|---------|------|----|-----------|
| ...     | ...  | .. | ...       |

### Breaking Changes Applied
- [list any code changes made for compatibility]

### Verification
- Build: PASS/FAIL
- Tests: PASS/FAIL (X/Y passing)
- Types: PASS/FAIL

### Skipped (manual action needed)
- [any packages that couldn't be auto-updated]
```

## Important Notes

- **Lock file detection**: Check for `yarn.lock`, `pnpm-lock.yaml`, `package-lock.json` to determine the Node.js package manager. Do not assume npm.
- **Monorepos**: If the project has workspaces (npm/yarn/pnpm workspaces, Lerna), run updates at the root level.
- **Virtual environments**: For Python, check if a venv is active before running pip commands. Activate it if found.
- **Selective updates**: If the user specifies particular packages or ecosystems, limit the update scope accordingly.
- **Dry run**: If the user asks for a check-only or dry-run, stop after Step 2 (reporting outdated packages) without updating.
- **Git safety**: Do NOT commit changes automatically. Leave that to the user.
