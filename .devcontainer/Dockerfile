# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM mcr.microsoft.com/devcontainers/base:ubuntu AS builder

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Node.js 24.x and Python pip with apt cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs python3-pip

# Install npm global packages with cache
RUN --mount=type=cache,target=/root/.npm \
    npm install -g @playwright/cli agent-browser

# Install uv (Python package manager for MCP servers)
RUN pip3 install --break-system-packages uv

# Install Playwright Chromium
RUN npx -y playwright install chromium --with-deps

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM mcr.microsoft.com/devcontainers/base:ubuntu AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/home/vscode/.cache/ms-playwright
ENV NODE_ENV=production

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y \
    nodejs \
    python3 \
    python3-pip \
    python3-venv \
    pipx \
    jq \
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
    libasound2t64 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Configure Polish locale
RUN if grep -q '^# pl_PL.UTF-8' /etc/locale.gen 2>/dev/null; then \
    sed -i '/pl_PL.UTF-8/s/^# //g' /etc/locale.gen && locale-gen; \
    fi

# Copy Node.js global packages from builder
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules

# Create symlinks for npm global packages (COPY doesn't include /usr/bin links)
RUN ln -sf /usr/lib/node_modules/@playwright/cli/playwright-cli.js /usr/bin/playwright-cli \
    && ln -sf /usr/lib/node_modules/agent-browser/bin/agent-browser.js /usr/bin/agent-browser

# Copy uv from builder (needed by MCP servers using uvx)
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx

# Copy Playwright browsers
COPY --chown=vscode:vscode --from=builder /root/.cache/ms-playwright /home/vscode/.cache/ms-playwright

RUN mkdir -p /tmp/playwright-output

USER vscode
