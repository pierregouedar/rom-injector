# Development

## Prerequisites

- Node 20+, `pnpm` (or `npm` / `yarn`).
- Python 3.11+ on the target (Steam Deck has this built-in).
- Decky Loader installed on the target.
- SSH access to the Deck (recommended: `passwd`, `sudo systemctl enable --now sshd`).

## Layout

```
rom-injector/
├── main.py            ← RPC façade
├── config.py          ← schema / IO / migrate / normalize
├── scanner.py         ← ROM + artwork scanning
├── sgdb.py            ← SteamGridDB client
├── logs.py            ← ring-buffer logger
├── plugin.json        ← Decky manifest
├── package.json
├── rollup.config.js
├── tsconfig.json
├── install.sh         ← one-shot installer
└── src/
    ├── index.tsx       ← orchestrator
    ├── backend.ts      ← callable bindings + types
    ├── steam.ts        ← SteamClient glue
    ├── i18n.ts         ← 6 locales
    ├── hooks/          ← state hooks
    └── components/     ← dumb UI panels
```

## Build

```bash
pnpm install
pnpm build      # one-shot (writes dist/index.js)
pnpm watch      # rollup -c -w
```

## Deploy to the Deck

### Over SSH

```bash
./install.sh deck@steamdeck.local
```

### Local (running the script on the Deck itself)

```bash
./install.sh
```

### Manual

```bash
rsync -av --delete --exclude node_modules --exclude .git \
  ./ deck@steamdeck.local:/home/deck/homebrew/plugins/rom-injector/
ssh deck@steamdeck.local sudo systemctl restart plugin_loader
```

Restart Decky, **not** Steam. Restarting Decky re-parses `plugin.json`, reloads `main.py`, and re-renders the TSX. Your added shortcuts stay put.

## Live-edit on the Deck

Decky hot-reloads the frontend on every build. Rsync `dist/index.js` over while `pnpm watch` is running for sub-second feedback.

## Backend debugging

- Logs go to `decky.logger` → stream with `journalctl --user -u plugin_loader -f` on the Deck.
- The ring-buffer tail is surfaced in-UI via **Refresh Logs**.
- Python exceptions in `Plugin` methods propagate to the frontend as thrown JS errors — check the CEF console.

## Frontend debugging

Enable Decky's "Allow Remote CEF Debugging" toggle, then on your dev machine:

```
http://<deck-ip>:8080
```

Pick the `SharedJSContext` target. The plugin's JS lives in that context — you can inspect `SteamClient`, run `SteamClient.Apps.RegisterForShortcutList(console.log)`, etc.

## Testing the Steam API surface

Safe to poke in the CEF console while Steam is running:

```js
// List existing shortcuts
SteamClient.Apps.RegisterForShortcutList(console.log);

// Add a scratch shortcut
const id = await SteamClient.Apps.AddShortcut("scratch", '"/bin/true"', '"/tmp"', "");

// Remove it
await SteamClient.Apps.RemoveShortcut(id);
```

## Common pitfalls

- **`exe` and `start_dir` must be double-quoted** — Steam stores them verbatim and the launcher expects quoted paths.
- **Always use forward slashes** in paths, even though Linux-only — Steam's C++ launcher does its own quoting.
- **Artwork ≥ 8 MiB is dropped** — Steam's binding will silently fail on very large base64 payloads.
- **Don't `PATCH` `shortcuts.vdf` at runtime** — Steam ignores it, and will overwrite you on shutdown.
- **Collection assignment can no-op** on old Steam clients without `AddAppsToCollection`. Not fatal.

## Lint / format

No linter wired in the base template. Recommended: `biome` or `prettier + eslint`. PRs welcome.

## Publishing

To submit to the Decky store:

1. Bump version in `plugin.json` + `package.json`.
2. Ensure `pnpm build` produces a clean `dist/index.js`.
3. Open a PR against `SteamDeckHomebrew/decky-plugin-database`.
