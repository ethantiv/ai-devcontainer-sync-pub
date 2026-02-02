# Claude Code & Gemini CLI Docker image for ARM64
# Multi-stage build for terminal-only AI development

# =============================================================================
# BUILDER STAGE
# =============================================================================
FROM debian:bookworm-slim AS builder

ARG NODE_VERSION=24
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg git unzip xz-utils \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @google/gemini-cli @playwright/cli agent-browser

RUN pip3 install --break-system-packages uv python-telegram-bot

RUN npx -y playwright install chromium --with-deps

# =============================================================================
# RUNTIME STAGE
# =============================================================================
FROM debian:bookworm-slim AS runtime

ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    DO_NOT_TRACK=1 \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    HOME=/home/${USERNAME} \
    PATH="/home/${USERNAME}/.claude/bin:/home/${USERNAME}/.local/bin:/home/${USERNAME}/.uv/bin:/usr/local/bin:${PATH}" \
    NODE_OPTIONS="--max-old-space-size=512"

# Core packages and Playwright Chromium dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg git jq unzip openssh-client python3 python3-pip \
    tmux locales \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Generate UTF-8 locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

# Node.js and GitHub CLI
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y nodejs gh \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder: npm packages, uv tools, Playwright browsers
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
COPY --from=builder /root/.cache/ms-playwright /opt/playwright

# Create symlinks for npm global packages (Claude Code installed via curl at runtime)
RUN ln -sf ../lib/node_modules/@google/gemini-cli/dist/index.js /usr/bin/gemini \
    && ln -sf ../lib/node_modules/@playwright/cli/playwright-cli.js /usr/bin/playwright-cli \
    && ln -sf ../lib/node_modules/agent-browser/bin/agent-browser.js /usr/bin/agent-browser

# Create non-root user with required directories
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && mkdir -p ${HOME}/.claude/scripts ${HOME}/.claude/skills ${HOME}/.agents ${HOME}/.gemini ${HOME}/projects \
    && mkdir -p ${HOME}/.cache/ms-playwright /tmp/playwright-output \
    && cp -r /opt/playwright/* ${HOME}/.cache/ms-playwright/ \
    && chown -R ${USERNAME}:${USERNAME} ${HOME} /tmp/playwright-output \
    && echo "alias cc='clear && claude'" >> ${HOME}/.bashrc \
    && echo 'loop() { local script="$(git rev-parse --show-toplevel)/loop/loop.sh"; local use_tmux=false; local args=(); for arg in "$@"; do if [[ "$arg" == "--tmux" ]]; then use_tmux=true; else args+=("$arg"); fi; done; if $use_tmux; then local session_name="$(basename "$PWD")"; if tmux has-session -t "$session_name" 2>/dev/null; then tmux attach -t "$session_name"; else tmux new-session -s "$session_name" -- "$script" "${args[@]}"; fi; else "$script" "${args[@]}"; fi; }' >> ${HOME}/.bashrc

# Copy configuration files for runtime sync to volume
COPY .devcontainer/configuration/CLAUDE.md.memory /opt/claude-config/CLAUDE.md
COPY .devcontainer/configuration/skills-plugins.txt /opt/claude-config/skills-plugins.txt
COPY .devcontainer/scripts/*.sh /opt/claude-config/scripts/
COPY .devcontainer/plugins/dev-marketplace /opt/claude-config/plugins/dev-marketplace
COPY docker/entrypoint.sh docker/setup-claude.sh /usr/local/bin/

RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/setup-claude.sh \
    && chown -R ${USERNAME}:${USERNAME} /opt/claude-config

VOLUME ["${HOME}/.claude", "${HOME}/.agents", "${HOME}/.gemini", "${HOME}/projects"]

USER ${USERNAME}
WORKDIR ${HOME}/projects

ENV CLAUDE_CONFIG_DIR=${HOME}/.claude \
    PLAYWRIGHT_BROWSERS_PATH=${HOME}/.cache/ms-playwright \
    PLAYWRIGHT_MCP_BROWSER=chromium \
    PLAYWRIGHT_MCP_NO_SANDBOX=true

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
