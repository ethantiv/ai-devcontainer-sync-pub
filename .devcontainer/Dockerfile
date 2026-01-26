# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM mcr.microsoft.com/devcontainers/base:ubuntu AS builder

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Node.js 24.x with apt cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs

# Install npm global packages with cache
RUN --mount=type=cache,target=/root/.npm \
    npm install -g @playwright/mcp

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

# Create symlink for playwright-cli
RUN ln -sf /usr/lib/node_modules/@playwright/mcp/playwright-cli.js /usr/bin/playwright-cli

# Copy Playwright browsers
COPY --chown=vscode:vscode --from=builder /root/.cache/ms-playwright /home/vscode/.cache/ms-playwright

# Create Chrome symlink for playwright-cli
RUN mkdir -p /opt/google/chrome && \
    CHROME_PATH=$(find /home/vscode/.cache/ms-playwright -name chrome -type f -path "*/chrome-linux/*" 2>/dev/null | head -1) && \
    if [ -n "$CHROME_PATH" ]; then ln -sf "$CHROME_PATH" /opt/google/chrome/chrome; fi

USER vscode
