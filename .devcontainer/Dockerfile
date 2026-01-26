# syntax=docker/dockerfile:1.6
# DevContainer with pre-built Claude, Gemini, Playwright, uv, specify-cli
# Optimized with BuildKit cache mounts for faster rebuilds

# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM mcr.microsoft.com/devcontainers/base:ubuntu AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js 24.x with apt cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs

# Install Claude Code (native binary - recommended method)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Install npm global packages with cache
RUN --mount=type=cache,target=/root/.npm \
    npm install -g \
        @google/gemini-cli \
        @playwright/mcp && \
    npm cache clean --force

# Install uv (Python package manager) and specify-cli with cache
# uv automatically downloads Python if not present
RUN --mount=type=cache,target=/root/.cache/uv \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv tool install specify-cli

# Install Playwright Chromium (cached in image)
RUN npx -y playwright install chromium --with-deps

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM mcr.microsoft.com/devcontainers/base:ubuntu AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js 24.x in runtime (needed for CLI tools)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends \
        nodejs \
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
RUN sed -i '/pl_PL.UTF-8/s/^# //g' /etc/locale.gen && locale-gen || true

# Copy Claude Code native binary from builder
COPY --from=builder /root/.local/bin/claude /usr/local/bin/claude

# Copy Node.js global packages from builder
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules

# Create symlinks for CLI tools
RUN ln -sf /usr/lib/node_modules/@google/gemini-cli/dist/index.js /usr/bin/gemini && \
    ln -sf /usr/lib/node_modules/@playwright/mcp/cli.js /usr/bin/playwright-cli

# Copy uv and tools from builder
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder /root/.local/bin/uvx /usr/local/bin/uvx
COPY --from=builder /root/.local/bin/specify /usr/local/bin/specify
COPY --from=builder /root/.local/share/uv /opt/uv-tools

# Copy Playwright browsers ONCE (no duplication)
COPY --chown=vscode:vscode --from=builder /root/.cache/ms-playwright /home/vscode/.cache/ms-playwright

# Create Chrome symlink for playwright-cli
RUN mkdir -p /opt/google/chrome && \
    CHROME_PATH=$(find /home/vscode/.cache/ms-playwright -name chrome -type f -path "*/chrome-linux/*" 2>/dev/null | head -1) && \
    if [ -n "$CHROME_PATH" ]; then ln -sf "$CHROME_PATH" /opt/google/chrome/chrome; fi

# Environment
ENV PLAYWRIGHT_BROWSERS_PATH=/home/vscode/.cache/ms-playwright
ENV NODE_ENV=production

# Ensure tmp directory exists for TMPDIR (volume seeding)
RUN mkdir -p /home/vscode/.claude/tmp && chown vscode:vscode /home/vscode/.claude/tmp
