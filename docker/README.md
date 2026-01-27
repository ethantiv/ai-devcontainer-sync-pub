# AI Code DevContainer

Lightweight Docker image with Claude Code, Gemini CLI, and development tools. Optimized for ARM64 (Raspberry Pi 5, Apple Silicon) but works on x86_64.

## Features

- **Claude Code** - Anthropic's AI coding assistant
- **Gemini CLI** - Google's AI assistant
- **Infrastructure tools** - Terraform, AWS CLI, GitHub CLI
- **Browser automation** - playwright-cli with Playwright/Chromium

## Quick Start

### Using Docker Compose (recommended)

```bash
cd docker

# Copy and edit .env file with your credentials
cp .env.example .env
# Edit .env with your tokens

# Build and run
docker compose up -d
docker compose exec claude bash
```

### Using Docker directly

```bash
# Build
docker build -t claude-terminal -f docker/Dockerfile .

# Run interactively
docker run -it --rm \
    -e CLAUDE_CODE_OAUTH_TOKEN="sk-ant-..." \
    -e GH_TOKEN="ghp_..." \
    -v $(pwd):/home/developer/projects \
    -v claude-config:/home/developer/.claude \
    claude-terminal
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | Claude Code OAuth token |
| `GH_TOKEN` | Yes | GitHub personal access token |

## Volumes

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `claude-config` | `/home/developer/.claude` | Claude configuration, plugins, settings |
| `gemini-config` | `/home/developer/.gemini` | Gemini CLI configuration |
| bind mount | `/home/developer/projects` | Your project files |

## Included Tools

| Tool | Command | Description |
|------|---------|-------------|
| Claude Code | `claude` | Anthropic's AI coding assistant |
| Gemini CLI | `gemini` | Google's AI assistant |
| specify-cli | `specify` | GitHub Spec-Kit |
| AWS CLI | `aws` | AWS command-line interface |
| GitHub CLI | `gh` | GitHub command-line tool |
| Terraform | `terraform` | Infrastructure as Code |
| playwright-cli | `playwright-cli` | Browser automation CLI |

## Pre-configured Plugins

On first run (with `CLAUDE_CODE_OAUTH_TOKEN` set), these are automatically installed:

**Official plugins (7):**
- agent-sdk-dev, code-simplifier, commit-commands
- feature-dev, frontend-design
- pyright-lsp, typescript-lsp

**External plugins/skills (3):**
- vercel-react-best-practices, web-design-guidelines
- playwright-cli

## MCP Servers

Pre-configured Model Context Protocol servers:

| Server | Description |
|--------|-------------|
| `aws-documentation` | Search and read AWS docs |
| `terraform` | Terraform/Terragrunt workflow and provider docs |

Verify with: `claude mcp list`

## Slash Commands

| Command | Description |
|---------|-------------|
| `/git-message` | Generate conventional commit messages |
| `/code-review` | Launch parallel code review agents |
| `/design-system` | Generate HTML design system templates |
| `/roadmap` | Generate or update ROADMAP.json |

## ARM64 Notes

This image is optimized for ARM64 architecture:

- **Claude Code**: Installed via npm (curl script has ARM64 issues - [#3569](https://github.com/anthropics/claude-code/issues/3569))
- **Terraform**: Uses `linux_arm64` binary
- **AWS CLI**: Uses `aarch64` package
- **Playwright/Chromium**: ARM64 compatible (adds ~500MB)

## Image Size

Approximately **4.5 GB** including Playwright, Chromium, and all dependencies for browser automation.

## Customization

### Modifying plugins

Edit `docker/setup-claude.sh` to change the list of installed plugins.

### Changing default settings

Claude settings are in `docker/setup-claude.sh` (`apply_claude_settings` function).

### Adding commands

Add `.md` files to `.devcontainer/commands/` before building.

## Troubleshooting

### Plugins not installed

Check if `CLAUDE_CODE_OAUTH_TOKEN` is set and valid:

```bash
echo $CLAUDE_CODE_OAUTH_TOKEN
claude mcp list
```

To force reinstall, remove the configured marker:

```bash
rm ~/.claude/.configured
/usr/local/bin/setup-claude.sh
```

### MCP servers not connecting

Ensure `uvx` is available and can download packages:

```bash
uvx --help
uvx awslabs.aws-documentation-mcp-server@latest --help
```

### Browser automation fails

playwright-cli requires Playwright browsers. Verify installation:

```bash
npx playwright install --help
ls ~/.cache/ms-playwright/
```

## Building for Different Architectures

```bash
# ARM64 only (default)
docker build -t claude-terminal -f docker/Dockerfile .

# Multi-architecture
docker buildx build --platform linux/arm64,linux/amd64 \
    -t claude-terminal -f docker/Dockerfile .
```
