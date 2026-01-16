# AI DevContainer Environment

Standalone DevContainer for multi-AI agent development with Claude Code and Gemini CLI.

## Quick Start

### 1. Create GitHub Token

[Create a Fine-grained personal access token](https://github.com/settings/personal-access-tokens) with `repo` and `workflow` permissions.

### 2. Configure Secret

**Codespaces**: Settings → Codespaces → Secrets → Add `GH_TOKEN`

**Local**: Create `.devcontainer/.env`:
```bash
GH_TOKEN=ghp_your_token_here
```

### 3. Open in DevContainer

Everything configures automatically on startup.

## What's Included

- **Claude Code** with custom slash commands (`/code-review`, `/git-message`)
- **Gemini CLI**
- **Local plugin marketplace** for development and testing
- **Vercel Skills** - React/Next.js best practices and UI/UX guidelines

## Common Commands

```bash
# Verify configuration
claude mcp list
claude plugin marketplace list

# Re-sync after changes
./.devcontainer/setup-env.sh
```

## Customization

Add custom commands, agents, or plugins in `.devcontainer/` directories, then rebuild or run `setup-env.sh`.

See [CLAUDE.md](CLAUDE.md) for detailed architecture.
