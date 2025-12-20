# AI DevContainer Environment

Standalone DevContainer for multi-AI agent development with Claude Code and Gemini CLI.

## Quick Start

### 1. Create GitHub Token

[Create a Fine-grained personal access tokens](https://github.com/settings/personal-access-tokens) with at least `Read access to metadata`, `Read and Write access to actions, code, issues, pull requests, and workflows` permissions.

### 2. Configure Secrets

**Codespaces**: Settings → Codespaces → Secrets → Add `GH_TOKEN`

**Local**: Create `.devcontainer/.env`:
```bash
GH_TOKEN=ghp_your_token_here
SSH_PRIVATE_KEY=base64_encoded_ssh_key  # Optional
```

To encode SSH key: `base64 -w 0 ~/.ssh/id_rsa`

### 3. Open in DevContainer

Everything configures automatically on startup.

## What's Included

### AI Agents
- **Claude Code** - installed via official installer
- **Gemini CLI** - installed via npm

### Custom Commands (synced to `~/.claude/commands/`)
- `/git-message` - Conventional commit messages
- `/polish-correction` - Polish language correction

### Custom Agents (synced to `~/.claude/agents/`)
- **architecture-analyzer** - Project structure analysis
- **code-explainer** - Code analysis without modifications

### Local Plugin Marketplace
`.devcontainer/plugins/dev-marketplace/` - develop and test plugins locally before publishing. Contains `placeholder-plugin` as template.

## Common Commands

```bash
# Verify configuration
claude mcp list
claude plugin marketplace list

# Re-sync after modifying commands/agents
./.devcontainer/setup-env.sh

# GitHub Spec-Kit (manual init per project)
specify init --here --ai claude

# GitHub operations
gh pr create --title "feat: description" --body "PR description"
```

## Persistent Storage

Docker volumes preserve configuration across rebuilds:
- `claude-code-config-${devcontainerId}` → `~/.claude`
- `gemini-cli-config-${devcontainerId}` → `~/.gemini`

## Environment

- **Base**: Ubuntu Noble + Docker-in-Docker
- **Tools**: GitHub CLI, Node.js, Python, Terraform, AWS CLI, Playwright
- **Timezone**: Europe/Warsaw
- **Locale**: pl_PL.UTF-8

## Customization

### Add Custom Command
1. Create `.md` file in `.devcontainer/commands/`
2. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Custom Agent
1. Create `.md` file in `.devcontainer/agents/`
2. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

### Add Local Plugin
1. Create plugin directory in `.devcontainer/plugins/dev-marketplace/`
2. Add `.claude-plugin/plugin.json`
3. Update `.devcontainer/plugins/dev-marketplace/.claude-plugin/marketplace.json`
4. Rebuild DevContainer or run `.devcontainer/setup-env.sh`

## Resources

- [Claude Code Plugins](https://github.com/anthropics/claude-code/tree/main/plugins)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
