# AI DevContainer Environment

Standalone DevContainer for multi-AI agent development with Claude Code and Gemini CLI.

## Quick Start

### 1. Create GitHub Token

[Create a Classic PAT](https://github.com/settings/tokens/new) with `repo`, `read:user`, and `workflow` permissions.

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
- **Claude Code** with plugins, commands, agents
- **Gemini CLI** with shared MCP servers

### MCP Servers (shared by all agents)
| Server | Description |
|--------|-------------|
| aws-docs | AWS documentation search and recommendations |
| aws-terraform | Terraform/Terragrunt execution, Checkov scanning |
| context7 | Library documentation from public registries |
| terraform | Terraform Registry (modules, providers, policies) |

### Claude Code Plugins (auto-installed)
| Plugin | Description |
|--------|-------------|
| commit-commands | `/commit`, `/commit-push-pr` |
| pr-review-toolkit | 6 specialized review agents |
| feature-dev | 7-phase feature workflow |
| plugin-dev | Plugin development toolkit |
| frontend-design | Production-grade UI generation |
| agent-sdk-dev | Agent SDK development |
| autonomous-builder¹ | Long-running app builder (`/build`, `/continue`) |

¹ From local marketplace (`.devcontainer/plugins/dev-marketplace/`)

### Custom Commands
- `/git-message` - Conventional commit messages
- `/polish-correction` - Polish language correction

### Specialized Agents
- **architecture-analyzer** - Project structure analysis
- **code-explainer** - Code analysis without modifications

## Common Commands

```bash
# Verify configuration
claude mcp list
claude plugin marketplace list

# Plugin management
claude plugin marketplace update
claude plugin disable plugin-name@claude-code-plugins

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
- **Tools**: GitHub CLI, Node.js, Python, Terraform, AWS CLI
- **Timezone**: Europe/Warsaw
- **Locale**: pl_PL.UTF-8

## Customization

See `CLAUDE.md` for architecture details and modification instructions.

## Resources

- [Claude Code Plugins](https://github.com/anthropics/claude-code/tree/main/plugins)
- [MCP Configuration](.devcontainer/configuration/mcp-servers.json)
