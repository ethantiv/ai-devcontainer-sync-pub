#!/bin/bash
# SSH aliases for Raspberry Pi host to exec into Coolify containers.
# Install: copy to ~/.bash_aliases on mirek@raspberrypi.local
#   scp docker/rpi-aliases.sh mirek@raspberrypi.local:~/.bash_aliases
#
# Usage:
#   cc      — exec into production claude-code container
#   dev-cc  — exec into dev claude-code container

# Exec into production claude-code container
cc() {
  local container
  container=$(sudo docker ps --format '{{.Names}}' | grep "^claude-code-")
  if [ -z "$container" ]; then
    echo "Error: production claude-code container not found" >&2
    return 1
  fi
  sudo docker exec -it "$container" bash
}

# Exec into dev claude-code container
dev-cc() {
  local container
  container=$(sudo docker ps --format '{{.Names}}' | grep "^dev-claude-code-")
  if [ -z "$container" ]; then
    echo "Error: dev claude-code container not found" >&2
    return 1
  fi
  sudo docker exec -it "$container" bash
}
