# ROM Injector

Decky Loader plugin for SteamOS. Adds ROM shortcuts to the Steam Library **live, without restarting Steam**, via Steam's internal `SteamClient.Apps.*` JS API — the same mechanism NonSteamLaunchers and Junk Store use.

Optional SteamGridDB integration fetches grid / hero / logo / icon artwork automatically.

## Features

- Real-time shortcut injection (no Steam restart, no Desktop-mode switch).
- Multiple ROM roots; per-extension emulator profiles; default + per-profile compat tool.
- Preview scan before sync (with progress bar during sync).
- Local artwork auto-discovery (`<rom>-grid.png`, `media/hero/<rom>.png`, …).
- SteamGridDB fetch for missing artwork, with 7-day disk cache + negative cache.
- Auto-assign every added shortcut to a Library collection (default `ROMs`).
- Dedupe via `RegisterForShortcutList` snapshot.
- Stale-shortcut cleanup (removes entries whose ROM file is gone).
- Undo last sync (one click, removes all appids added in the last run).
- Import / export config via clipboard.
- Inline validation: roots/exes checked on disk, flagged in red if missing.
- In-panel log tail (500-line ring buffer).
- 6 UI locales: English, Français, Deutsch, Italiano, Español, Nederlands (auto-detected, override-able).

## Install

The installer needs only `curl` (or `wget`), `tar`, and `systemctl` — **no node / npm / pnpm required on the Deck**. Prebuilt release tarballs are published on GitHub Releases via CI.

### One-liner (pulls the latest release on the Deck, in Desktop Mode)

```bash
curl -L https://github.com/pierregouedar/rom-injector/releases/latest/download/install.sh -o /tmp/rom-injector-install.sh \
  && sh /tmp/rom-injector-install.sh --remote
```

The link above redirects to whichever version is currently tagged **latest** on GitHub — no manual bumping needed. The script fetches the matching tarball the same way. If you haven't published a release yet, fall back to the `main` branch script:

```bash
curl -L https://raw.githubusercontent.com/pierregouedar/rom-injector/main/install.sh -o /tmp/rom-injector-install.sh \
  && sh /tmp/rom-injector-install.sh --remote
```

### From a clone

```bash
./install.sh --remote              # download latest release, then install locally
./install.sh --version v0.2.0      # pin a specific release
./install.sh                       # install from the local folder (requires dist/index.js already built)
```

### Remote deploy over SSH (from your dev machine)

```bash
./install.sh --host deck@steamdeck.local --remote    # ship the release tarball to the Deck
./install.sh --host deck@steamdeck.local             # ship the current local tree (requires local build)
```

### Uninstall

```bash
./install.sh --uninstall
./install.sh --host deck@steamdeck.local --uninstall
```

### Building from source (developer only)

Only needed if you want to modify the plugin. End users should use `--remote`.

1. `pnpm install && pnpm build`
2. `./install.sh` (copies the just-built tree — no build step inside the script).

## First-run setup

1. Open the Decky quick-access menu → ROM Injector.
2. Pick a language (auto-detected from system locale).
3. Add a ROM root (default `/home/deck/Emulation/roms`). Use the red/green validation marker to confirm the path exists.
4. Review emulator profiles. Defaults target Flatpak emulators shipped by EmuDeck (mGBA, RetroArch cores for NES/SNES/N64). Override any `exe`, `args`, or `compat_tool`.
5. (Optional) Enable SteamGridDB, paste an API key (see below).
6. Press **Preview Sync** to see what will be added.
7. Press **Confirm Sync** to inject shortcuts.
8. Open the Library — ROMs appear instantly under "Non-Steam".

## SteamGridDB

SGDB does not expose a programmatic way to retrieve a user's API key. Closest-to-auto flow:

1. In the plugin, tap **Open SGDB API page** — Steam's built-in browser opens on the prefs page. Steam auto-logs-in via OpenID.
2. Generate / copy the key on that page.
3. Back in the plugin, tap **Paste key from Clipboard**. Key is validated, saved, enabled, and tested automatically.

Artwork preference order per ROM: local file → SGDB cache → SGDB fetch.

## Config file

Stored at `$DECKY_PLUGIN_SETTINGS_DIR/config.json`. See [docs/CONFIG.md](docs/CONFIG.md) for the schema. Use the in-app Import/Export buttons to move configs between Decks.

## Safety

- Writes to `shortcuts.vdf` happen **only when Steam shuts down** — in-memory mutations persist on the next clean exit. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#why-not-write-shortcutsvdf-directly) for rationale.
- Stale-cleanup and Undo call `SteamClient.Apps.RemoveShortcut`; no external `shortcuts.vdf` editing.
- Uses the same internal APIs as Decky itself, NonSteamLaunchers, and Junk Store. See [docs/TOS.md](docs/TOS.md) for a frank ToS / compliance breakdown.

## Development

Build, debug, hack:

```bash
pnpm install
pnpm watch      # rollup watch for src/
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## License

MIT.
