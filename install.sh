#!/usr/bin/env bash
# ROM Injector — end-user installer for SteamOS / Steam Deck.
# No node / npm / pnpm required. Only: curl (or wget), tar, rsync, systemctl.
#
# Usage:
#   ./install.sh                       # install locally (on the Deck) from this folder
#   ./install.sh --remote              # download latest release tarball and install
#   ./install.sh --host <user@host>    # install over SSH from this folder
#   ./install.sh --uninstall           # remove local install
#   ./install.sh --host <user@host> --uninstall
#   ./install.sh --version vX.Y.Z      # pin a specific release (default: latest)

set -euo pipefail

PLUGIN_NAME="rom-injector"
PLUGIN_DIR_DEFAULT="/home/deck/homebrew/plugins/${PLUGIN_NAME}"
SERVICE="plugin_loader"
GH_OWNER="pierregouedar"
GH_REPO="rom-injector"
RELEASE_ASSET="${PLUGIN_NAME}.tar.gz"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null || echo "$PWD")"

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info()  { color '1;34' "==> $*"; }
ok()    { color '1;32' "==> $*"; }
warn()  { color '1;33' "!!  $*"; }
fail()  { color '1;31' "!!  $*"; exit 1; }

usage() {
  sed -n 's/^# \{0,1\}//p' "$0" | sed -n '2,12p'
  exit 0
}

# ── flags ──
MODE="install"
SOURCE="local"       # local | remote
HOST=""
VERSION="latest"

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)       usage;;
    --uninstall)     MODE="uninstall";;
    --remote)        SOURCE="remote";;
    --host)          HOST="${2:-}"; [ -z "$HOST" ] && fail "--host needs a value"; shift;;
    --version)       VERSION="${2:-}"; [ -z "$VERSION" ] && fail "--version needs a value"; shift;;
    *)               warn "ignoring unknown arg: $1";;
  esac
  shift
done

# ── tooling checks ──
has() { command -v "$1" >/dev/null 2>&1; }

fetcher() {
  if has curl; then echo "curl -fSL -o"
  elif has wget; then echo "wget -qO"
  else fail "neither curl nor wget is installed"
  fi
}

# ── helpers ──
release_url() {
  local tag="$1"
  if [ "$tag" = "latest" ]; then
    echo "https://github.com/${GH_OWNER}/${GH_REPO}/releases/latest/download/${RELEASE_ASSET}"
  else
    echo "https://github.com/${GH_OWNER}/${GH_REPO}/releases/download/${tag}/${RELEASE_ASSET}"
  fi
}

download_release() {
  local dest_dir="$1"
  local url; url="$(release_url "$VERSION")"
  local fetch; fetch="$(fetcher)"
  info "downloading release tarball: $url"
  mkdir -p "$dest_dir"
  local tarball="$dest_dir/${RELEASE_ASSET}"
  # shellcheck disable=SC2086
  $fetch "$tarball" "$url"
  info "unpacking into $dest_dir"
  tar -xzf "$tarball" -C "$dest_dir"
  rm -f "$tarball"
  ok "release unpacked"
}

verify_build_present() {
  local dir="$1"
  [ -f "$dir/dist/index.js" ] || fail "missing $dir/dist/index.js — build on a dev machine (\`pnpm install && pnpm build\`) or use --remote to download a prebuilt release"
  [ -f "$dir/main.py" ]       || fail "missing $dir/main.py"
  [ -f "$dir/plugin.json" ]   || fail "missing $dir/plugin.json"
}

copy_plugin() {
  local src="$1" dest="$2"
  info "copying plugin files to $dest"
  mkdir -p "$dest"
  if has rsync; then
    rsync -a --delete \
      --exclude node_modules --exclude .git --exclude '__pycache__' \
      --exclude 'src/**/*.map' --exclude '*.tar.gz' \
      "$src/" "$dest/"
  else
    warn "rsync not found, falling back to cp -r"
    rm -rf "$dest"
    mkdir -p "$dest"
    (cd "$src" && tar cf - \
      --exclude node_modules --exclude .git --exclude '__pycache__' \
      --exclude 'src/**/*.map' --exclude '*.tar.gz' \
      .) | (cd "$dest" && tar xf -)
  fi
  ok "files in place"
}

restart_decky() {
  info "restarting $SERVICE"
  if systemctl --user list-units --type=service 2>/dev/null | grep -q "$SERVICE"; then
    systemctl --user restart "$SERVICE" && return 0
  fi
  if has sudo && sudo -n systemctl restart "$SERVICE" 2>/dev/null; then
    return 0
  fi
  warn "could not restart $SERVICE automatically — toggle Decky Loader from Settings or reboot"
}

ssh_run() {
  local host="$1"; shift
  ssh -o StrictHostKeyChecking=accept-new "$host" "$@"
}

# ── remote-over-SSH flow ──
remote_install() {
  local host="$1"
  has ssh   || fail "ssh required locally for --host"
  has rsync || fail "rsync required locally for --host"

  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "$staging"' EXIT

  if [ "$SOURCE" = "remote" ]; then
    download_release "$staging"
  else
    verify_build_present "$SCRIPT_DIR"
    info "copying local tree to staging"
    rsync -a --delete \
      --exclude node_modules --exclude .git --exclude '__pycache__' \
      --exclude 'src/**/*.map' --exclude '*.tar.gz' \
      "$SCRIPT_DIR/" "$staging/"
  fi

  info "ensuring remote plugin dir exists on $host"
  ssh_run "$host" "mkdir -p '$PLUGIN_DIR_DEFAULT'"
  info "syncing to $host:$PLUGIN_DIR_DEFAULT"
  rsync -az --delete "$staging/" "$host:$PLUGIN_DIR_DEFAULT/"
  info "restarting Decky on $host"
  ssh_run "$host" "sudo -n systemctl restart $SERVICE 2>/dev/null || systemctl --user restart $SERVICE || true"
  ok "installed on $host"
}

remote_uninstall() {
  local host="$1"
  has ssh || fail "ssh required locally for --host"
  info "removing $PLUGIN_DIR_DEFAULT on $host"
  ssh_run "$host" "rm -rf '$PLUGIN_DIR_DEFAULT' && (sudo -n systemctl restart $SERVICE 2>/dev/null || systemctl --user restart $SERVICE || true)"
  ok "uninstalled on $host"
}

# ── local flow ──
local_install() {
  [ -d "/home/deck/homebrew" ] || warn "/home/deck/homebrew not found — is this a Steam Deck with Decky Loader?"

  if [ "$SOURCE" = "remote" ]; then
    local staging
    staging="$(mktemp -d)"
    trap 'rm -rf "$staging"' EXIT
    download_release "$staging"
    copy_plugin "$staging" "$PLUGIN_DIR_DEFAULT"
  else
    verify_build_present "$SCRIPT_DIR"
    copy_plugin "$SCRIPT_DIR" "$PLUGIN_DIR_DEFAULT"
  fi

  restart_decky
  ok "installed at $PLUGIN_DIR_DEFAULT"
}

local_uninstall() {
  info "removing $PLUGIN_DIR_DEFAULT"
  rm -rf "$PLUGIN_DIR_DEFAULT"
  restart_decky
  ok "uninstalled"
}

# ── dispatch ──
if [ -n "$HOST" ]; then
  case "$MODE" in
    install)   remote_install   "$HOST";;
    uninstall) remote_uninstall "$HOST";;
  esac
else
  case "$MODE" in
    install)   local_install;;
    uninstall) local_uninstall;;
  esac
fi
