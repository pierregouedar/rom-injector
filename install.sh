#!/bin/bash
# ROM Injector — installation script for SteamOS / Steam Deck.
# Based on the allycenter installer pattern.
set -e

PLUGIN_NAME="ROM Injector"
PLUGIN_DIR="$HOME/homebrew/plugins/$PLUGIN_NAME"
REPO_OWNER="pierregouedar"
REPO_NAME="rom-injector"
SERVICE="plugin_loader"

TEMP_FILES=()
cleanup() {
  if [ ${#TEMP_FILES[@]} -gt 0 ]; then
    for f in "${TEMP_FILES[@]}"; do rm -rf "$f" 2>/dev/null || true; done
  fi
}
trap cleanup EXIT

echo "================================"
echo "  ROM Injector Installer"
echo "================================"
echo ""

# ── env checks ──
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
  echo "Error: Linux / SteamOS only."
  exit 1
fi

if [ ! -d "$HOME/homebrew/plugins" ]; then
  echo "Error: Decky Loader not detected at \$HOME/homebrew/plugins."
  echo "Install Decky Loader first: https://decky.xyz"
  exit 1
fi

# ── existing install ──
if [ -d "$PLUGIN_DIR" ]; then
  echo "Existing installation at: $PLUGIN_DIR"
  read -p "Remove and reinstall? (y/N): " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
  fi
  sudo rm -rf "$PLUGIN_DIR"
fi

# Also nuke any legacy lowercase folder from older installer versions
if [ -d "$HOME/homebrew/plugins/rom-injector" ]; then
  echo "Removing legacy lowercase install at $HOME/homebrew/plugins/rom-injector..."
  sudo rm -rf "$HOME/homebrew/plugins/rom-injector"
fi

# ── create plugin dir (owned by user, not root, so Decky can read + we can write) ──
echo "Creating plugin directory (sudo needed)..."
sudo mkdir -p "$PLUGIN_DIR"
sudo chown -R "$USER:$USER" "$PLUGIN_DIR"

# ── find latest release ──
echo "Querying GitHub for latest release..."
RELEASE_JSON="$(curl -fsSL "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest")"
DOWNLOAD_URL="$(printf '%s' "$RELEASE_JSON" | grep -o '"browser_download_url": *"[^"]*\.zip"' | head -1 | cut -d '"' -f 4)"

if [ -z "$DOWNLOAD_URL" ]; then
  echo "Error: no .zip asset found on the latest release."
  echo "See: https://github.com/$REPO_OWNER/$REPO_NAME/releases"
  exit 1
fi

echo "Downloading: $DOWNLOAD_URL"
TEMP_ZIP="$(mktemp --suffix=.zip)"
TEMP_FILES+=("$TEMP_ZIP")

if ! curl -fL "$DOWNLOAD_URL" -o "$TEMP_ZIP"; then
  echo "Error: download failed."
  exit 1
fi

echo "Extracting to $PLUGIN_DIR..."
if ! command -v unzip >/dev/null 2>&1; then
  echo "Error: 'unzip' is not installed. Install it first (Deck ships with it)."
  exit 1
fi
unzip -q -o "$TEMP_ZIP" -d "$PLUGIN_DIR"

# ── post-check ──
echo ""
echo "Post-install check:"
ALL_OK=1
for f in main.py plugin.json dist/index.js; do
  if [ -f "$PLUGIN_DIR/$f" ]; then
    echo "  ok       $f"
  else
    echo "  MISSING  $f"
    ALL_OK=0
  fi
done
chmod -R 755 "$PLUGIN_DIR"

if [ $ALL_OK -ne 1 ]; then
  echo "Error: some expected files are missing — installation incomplete."
  exit 1
fi

# ── restart Decky ──
echo ""
echo "Restarting Decky Loader..."
if sudo systemctl restart "$SERVICE" 2>/dev/null; then
  echo "✓ $SERVICE restarted."
else
  echo "⚠ could not restart $SERVICE — run:  sudo systemctl restart $SERVICE"
fi

echo ""
echo "================================"
echo "  Installation complete"
echo "================================"
echo "  Path:   $PLUGIN_DIR"
echo "  Name:   $PLUGIN_NAME"
echo ""
echo "Open the Decky quick-access menu — ROM Injector should be listed."
