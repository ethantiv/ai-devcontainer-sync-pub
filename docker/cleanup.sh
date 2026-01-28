#!/bin/bash
# Complete cleanup of Docker Compose resources
# Removes containers, volumes, images, networks, and build cache

set -e

cd "$(dirname "$0")"

echo "🧹 Cleaning up Docker Compose resources..."

# Stop and remove containers, volumes, images, networks
docker compose down -v --rmi all --remove-orphans 2>/dev/null || true

# Prune build cache
echo "🗑️  Pruning build cache..."
docker builder prune -f

echo "✅ Cleanup complete!"
