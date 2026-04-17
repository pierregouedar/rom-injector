# Architecture

## Bird's-eye view

```
┌─ Backend (Python, Decky) ───────┐        ┌─ Frontend (React/TSX) ─────────┐
│  config.py  — schema / IO       │        │  hooks/  — state + side effects │
│  scanner.py — rom + artwork     │  ◄──►  │  components/ — UI panels        │
│  sgdb.py    — SteamGridDB       │  RPC   │  steam.ts   — SteamClient glue  │
│  logs.py    — ring handler      │        │  backend.ts — callable bindings │
│  main.py    — Plugin RPC façade │        │  i18n.ts    — 6 locales         │
└─────────────────────────────────┘        └─────────────────────────────────┘
              ▲                                          │
              │                                          ▼
              │                            ┌─ Steam internal JS API ────────┐
              │                            │  SteamClient.Apps.AddShortcut   │
              └── shortcuts.vdf (persisted │  .SetCustomArtworkForApp        │
                   only on Steam shutdown) │  .RegisterForShortcutList       │
                                           │  .RemoveShortcut / CompatTool   │
                                           │  collectionStore.Add…           │
                                           └────────────────────────────────┘
```

## Why not write `shortcuts.vdf` directly

- Steam reads `shortcuts.vdf` **once**, at client startup. No inotify, no DBus refresh signal, no socket command.
- Steam owns the in-memory `CShortcutsStore` for the life of the process. On shutdown it serializes *its* in-memory store to disk — **overwriting** any external edits you made at runtime.
- The only documented mutation path that persists is mutating the in-memory store via `SteamClient.Apps.*` (privileged JS globals injected into pages on `steamloopback.host`). Library reflects changes instantly; `shortcuts.vdf` is written on the next clean Steam shutdown.

## Frontend bridge vs CEF websocket

Two ways to reach `SteamClient.Apps.*`:

1. **Frontend bridge (what this plugin uses)** — Decky plugin TSX runs inside the `SharedJSContext` CEF page, so `SteamClient` is directly in scope. No websocket, no port assumption, no dependency on `-cef-enable-debugging`.
2. **CEF remote debugger** — external script connects to `127.0.0.1:8080/json`, finds the `SharedJSContext` target, sends `Runtime.evaluate` over the CDP websocket. Used by NonSteamLaunchers because it runs outside Decky.

This plugin keeps a passive CEF probe as a diagnostic (useful when troubleshooting other tools) but never depends on the port being open.

## Backend modules

| File | Purpose | External deps |
|------|---------|---------------|
| `config.py`  | Schema, default values, `load` / `save` / `migrate` / `normalize` | `decky` |
| `scanner.py` | `vdf_quote`, icon + artwork discovery, `scan_root` | `decky` (for log warnings) |
| `sgdb.py`    | SteamGridDB v2 API client, disk cache, negative cache | stdlib only |
| `logs.py`    | 500-line ring buffer logging handler | stdlib only |
| `main.py`    | `Plugin` class — thin RPC façade over the above | `decky` |

Each non-`main.py` module is importable in isolation; no module knows about the `Plugin` class or the RPC layer.

## Frontend modules

### Hooks (`src/hooks/`)

| Hook | Owns |
|------|------|
| `useConfig`     | Current config, dirty flag, mutate/persist/reset/replace |
| `useValidation` | Disk-existence report for roots + profile exes |
| `usePreview`    | Scan results, scan status |
| `useSync`       | Progress, undo count, `runSync` / `cleanStale` / `undoLast` |
| `useLogs`       | Backend log tail |
| `useSgdb`       | SGDB-specific side effects (open login page, paste key, test, clear cache) |

### Components (`src/components/`)

One panel per concern. All panels are dumb: props in, callbacks out. Translation function `t` is passed explicitly (no context) so each panel is easy to test.

### Top-level (`src/index.tsx`)

Wires hooks to components and owns no state except `busy` and last CEF probe result. Houses a single `notify(t, key, { body, vars })` helper for consistent toast calls.

## Sync flow

```
user taps Sync
  └─ persist config if dirty
      └─ getRomsToSync()                          ← backend scans + SGDB enrich
          └─ snapshotShortcuts()                  ← read existing via RegisterForShortcutList
              └─ for each rom:
                  ├─ dedupe check (exe|launch_opts set)
                  ├─ AddShortcut(name, exe, startDir, launchOpts) → appid
                  ├─ SetShortcutIcon / LaunchOptions / CompatTool
                  ├─ SetCustomArtworkForApp × {grid, hero, logo, icon}
                  └─ collectionStore.AddAppsToCollection(id, [appid])
          └─ recordLastSync(appids)               ← persist for Undo
```

Cleanup and Undo invert the same plumbing, calling `RemoveShortcut`.

## Dedupe key

Shortcut identity = `${exe}|${launch_opts}`. `launch_opts` already embeds the quoted ROM path, so renaming ROMs is detected as change (old entry becomes stale, new one added). Backend and frontend build the key the same way after stripping outer quotes — any divergence here produces phantom dupes.

## Persistence files

All under `$DECKY_PLUGIN_SETTINGS_DIR`:

- `config.json` — user-editable.
- `last_sync.json` — appids added in the most recent sync, used by Undo.
- `sgdb_cache/` — fetched artwork cache + `.miss` negative-cache sentinels.
