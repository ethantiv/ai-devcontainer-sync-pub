#!/bin/bash
# SSH aliases for Raspberry Pi host to exec into Coolify containers.
# Install: copy to ~/.bash_aliases on mirek@raspberrypi.local
#   scp docker/rpi-aliases.sh mirek@raspberrypi.local:~/.bash_aliases
#
# Usage:
#   cc      — exec into claude-code container

# Exec into claude-code container
cc() {
  local container
  container=$(sudo docker ps --format '{{.Names}}' | grep "^claude-code-")
  if [ -z "$container" ]; then
    echo "Error: claude-code container not found" >&2
    return 1
  fi
  sudo docker exec -it "$container" bash
}
