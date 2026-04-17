#!/usr/bin/env bash
# ROM Injector — one-shot installer for SteamOS / Steam Deck.
#
# Usage:
#   ./install.sh                    # install locally (run ON the Deck)
#   ./install.sh <host>             # remote install over SSH (e.g. deck@steamdeck.local)
#   ./install.sh --uninstall        # remove local install
#   ./install.sh <host> --uninstall # remove remote install

set -euo pipefail

PLUGIN_NAME="rom-injector"
PLUGIN_DIR_DEFAULT="/home/deck/homebrew/plugins/${PLUGIN_NAME}"
SERVICE="plugin_loader"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info()  { color '1;34' "==> $*"; }
ok()    { color '1;32' "==> $*"; }
warn()  { color '1;33' "!!  $*"; }
fail()  { color '1;31' "!!  $*"; exit 1; }

usage() {
  sed -n 's/^# \{0,1\}//p' "$0" | head -n 10
  exit 0
}

HOST=""
MODE="install"
for arg in "$@"; do
  case "$arg" in
    -h|--help)       usage;;
    --uninstall)     MODE="uninstall";;
    *@*|*.local|*.*) HOST="$arg";;
    *)               warn "ignoring unknown argument: $arg";;
  esac
done

# ── shared actions ──
local_build() {
  command -v pnpm >/dev/null 2>&1 || fail "pnpm not installed. Run: npm i -g pnpm"
  info "installing node deps"
  (cd "$SCRIPT_DIR" && pnpm install --frozen-lockfile 2>/dev/null || pnpm install)
  info "building frontend"
  (cd "$SCRIPT_DIR" && pnpm build)
  [ -f "$SCRIPT_DIR/dist/index.js" ] || fail "build did not produce dist/index.js"
  ok "frontend built"
}

local_copy_to() {
  local dest="$1"
  info "copying plugin to $dest"
  mkdir -p "$dest"
  rsync -a --delete \
    --exclude node_modules --exclude .git --exclude '__pycache__' \
    --exclude 'src/**/*.map' \
    "$SCRIPT_DIR/" "$dest/"
  ok "plugin files in place"
}

local_restart_decky() {
  info "restarting $SERVICE"
  if systemctl --user list-units --type=service | grep -q "$SERVICE"; then
    systemctl --user restart "$SERVICE" && return 0
  fi
  if command -v sudo >/dev/null 2>&1 && sudo -n systemctl restart "$SERVICE" 2>/dev/null; then
    return 0
  fi
  warn "could not restart $SERVICE automatically — reboot Decky Loader manually"
}

local_uninstall() {
  info "removing $PLUGIN_DIR_DEFAULT"
  rm -rf "$PLUGIN_DIR_DEFAULT"
  ok "uninstalled"
}

# ── remote actions ──
remote_push() {
  local host="$1"
  command -v rsync >/dev/null 2>&1 || fail "rsync required locally"
  info "ensuring pnpm+build locally (frontend bundled before deploy)"
  local_build
  info "syncing to $host:$PLUGIN_DIR_DEFAULT"
  ssh "$host" "mkdir -p '$PLUGIN_DIR_DEFAULT'"
  rsync -az --delete \
    --exclude node_modules --exclude .git --exclude '__pycache__' \
    --exclude 'src/**/*.map' \
    "$SCRIPT_DIR/" "$host:$PLUGIN_DIR_DEFAULT/"
  info "restarting Decky on $host"
  ssh "$host" "sudo -n systemctl restart $SERVICE || systemctl --user restart $SERVICE || true"
  ok "installed on $host"
}

remote_uninstall() {
  local host="$1"
  info "removing $PLUGIN_DIR_DEFAULT on $host"
  ssh "$host" "rm -rf '$PLUGIN_DIR_DEFAULT' && (sudo -n systemctl restart $SERVICE || systemctl --user restart $SERVICE || true)"
  ok "uninstalled on $host"
}

# ── dispatch ──
if [ -n "$HOST" ]; then
  case "$MODE" in
    install)   remote_push      "$HOST";;
    uninstall) remote_uninstall "$HOST";;
  esac
else
  case "$MODE" in
    install)
      # Are we on the Deck?
      if [ ! -d "/home/deck/homebrew" ]; then
        warn "'/home/deck/homebrew' not found — pass a host arg to deploy remotely"
        fail "no local Decky install detected"
      fi
      local_build
      local_copy_to "$PLUGIN_DIR_DEFAULT"
      local_restart_decky
      ok "installed at $PLUGIN_DIR_DEFAULT"
      ;;
    uninstall) local_uninstall;;
  esac
fi
