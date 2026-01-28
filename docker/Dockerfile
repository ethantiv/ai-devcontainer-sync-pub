# Lightweight Claude Code & Gemini CLI Docker image for ARM64
# Multi-stage build optimized for terminal-only development

# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM debian:bookworm-slim AS builder

ARG TERRAFORM_VERSION=1.12.2
ARG NODE_VERSION=20

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    git \
    unzip \
    xz-utils \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform (ARM64)
RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_arm64.zip" -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && rm /tmp/terraform.zip \
    && chmod +x /usr/local/bin/terraform

# Install npm global packages
# Note: Claude Code must be installed via npm (not curl script) due to ARM64 bug #3569
RUN npm install -g \
    @anthropic-ai/claude-code \
    @google/gemini-cli \
    @playwright/cli \
    agent-browser

# Install uv (Python package manager)
RUN pip3 install --break-system-packages uv

# Install Playwright with Chromium for playwright-cli
RUN npx -y playwright install chromium --with-deps

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM debian:bookworm-slim AS runtime

ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV DO_NOT_TRACK=1
ENV HOME=/home/${USERNAME}
ENV PATH="${HOME}/.local/bin:${HOME}/.uv/bin:/usr/local/bin:${PATH}"
ENV NODE_OPTIONS="--max-old-space-size=512"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    git \
    jq \
    unzip \
    openssh-client \
    python3 \
    python3-pip \
    # Chromium dependencies for Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js runtime
COPY --from=builder /usr/bin/node /usr/bin/node
COPY --from=builder /usr/bin/npm /usr/bin/npm
COPY --from=builder /usr/bin/npx /usr/bin/npx
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules

# Install GitHub CLI (arm64)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2 (ARM64)
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip

# Copy Terraform from builder
COPY --from=builder /usr/local/bin/terraform /usr/local/bin/terraform

# Create symlinks for npm global packages (they're in /usr/lib/node_modules)
# Note: bin paths vary by package, using the actual entry points
RUN ln -sf ../lib/node_modules/@anthropic-ai/claude-code/cli.js /usr/bin/claude \
    && ln -sf ../lib/node_modules/@google/gemini-cli/dist/index.js /usr/bin/gemini \
    && ln -sf ../lib/node_modules/@playwright/cli/playwright-cli.js /usr/bin/playwright-cli \
    && ln -sf ../lib/node_modules/agent-browser/bin/agent-browser.js /usr/bin/agent-browser

# Copy uv and tools from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx

# Copy Playwright browsers
COPY --from=builder /root/.cache/ms-playwright /opt/playwright

# Create non-root user
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && mkdir -p ${HOME}/.claude ${HOME}/.claude/scripts ${HOME}/.claude/skills ${HOME}/.gemini ${HOME}/projects \
    && chown -R ${USERNAME}:${USERNAME} ${HOME} \
    && echo "alias cc='clear && claude'" >> ${HOME}/.bashrc

# Setup Playwright for non-root user
RUN mkdir -p ${HOME}/.cache \
    && cp -r /opt/playwright ${HOME}/.cache/ms-playwright \
    && chown -R ${USERNAME}:${USERNAME} ${HOME}/.cache

# Copy configuration files to /opt (for runtime sync to volume)
COPY .devcontainer/configuration/CLAUDE.md.memory /opt/claude-config/CLAUDE.md
COPY .devcontainer/scripts/*.sh /opt/claude-config/scripts/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/setup-claude.sh /usr/local/bin/setup-claude.sh

# Set permissions
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/setup-claude.sh \
    && chown -R ${USERNAME}:${USERNAME} ${HOME}/.claude /opt/claude-config

# Create Playwright output directory
RUN mkdir -p /tmp/playwright-output && chown ${USERNAME}:${USERNAME} /tmp/playwright-output

# Declare volumes for persistence
VOLUME ["${HOME}/.claude", "${HOME}/.gemini", "${HOME}/projects"]

# Switch to non-root user
USER ${USERNAME}
WORKDIR ${HOME}/projects

# Environment for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=${HOME}/.cache/ms-playwright

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
