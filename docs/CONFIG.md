# Config Reference

Config lives at `$DECKY_PLUGIN_SETTINGS_DIR/config.json`. On the Steam Deck that resolves to:

```
/home/deck/homebrew/settings/rom-injector/config.json
```

## Schema

```jsonc
{
  "roots": ["/home/deck/Emulation/roms"],
  "default_compat_tool": "proton_experimental",
  "assign_collection": "ROMs",
  "steamgriddb_api_key": "",
  "steamgriddb_enabled": false,
  "language": "en",                     // optional: en|fr|de|it|es|nl
  "profiles": [
    {
      "ext": ".gba",
      "exe": "/usr/bin/flatpak",
      "args": "run io.mgba.mGBA {rom}",
      "compat_tool": ""                 // blank = use default_compat_tool
    }
  ]
}
```

## Field reference

| Field | Type | Notes |
|-------|------|-------|
| `roots` | `string[]` | Directories scanned recursively. Empty strings stripped on save. |
| `default_compat_tool` | `string` | Proton / compat tool id applied to every profile with empty `compat_tool`. Use `""` or `proton_experimental` for native Linux emulators. |
| `assign_collection` | `string` | Library collection name. Added shortcuts are inserted into this collection; created if missing. Empty string = skip. |
| `steamgriddb_api_key` | `string` | Bearer key from `steamgriddb.com/profile/preferences/api`. Empty disables fetching even if `steamgriddb_enabled = true`. |
| `steamgriddb_enabled` | `boolean` | Master toggle for SGDB fetching. |
| `language` | `string?` | One of `en`, `fr`, `de`, `it`, `es`, `nl`. If unset, UI auto-detects from `navigator.language`. |
| `profiles` | `Profile[]` | Per-extension emulator rules. |

### `Profile` object

| Field | Type | Notes |
|-------|------|-------|
| `ext` | `string` | ROM extension, with or without leading dot. Normalized to lowercase + dot-prefix on save. |
| `exe` | `string` | Absolute path to emulator executable (or launcher like `/usr/bin/flatpak`). Required. |
| `args` | `string` | Argument template. `{rom}` is replaced with the quoted absolute ROM path. Defaults to `"{rom}"` if blank. |
| `compat_tool` | `string` | Per-profile compat override. Empty = inherit `default_compat_tool`. |

Profiles with missing `ext` or `exe` are dropped on save.

## Migration

Legacy single-root configs (`{"root": "...", "compat_tool": "..."}`) are auto-migrated to the multi-root shape on first load. Legacy fields are removed.

## Runtime state (not user-editable)

- `last_sync.json` — `{"appids": [number]}`. Written after each sync; consumed by Undo; cleared after Undo.
- `sgdb_cache/` — `<hash>-<kind>.{png,jpg}` blobs, `<hash>-<kind>.json` metadata, `<hash>-<kind>.miss` negative-cache sentinels (7-day TTL).

## Import / Export

The UI Import/Export buttons read/write the config JSON via the system clipboard. Server-side `import_config` runs the same `normalize()` path as manual edits, so invalid entries are silently cleaned rather than rejected.

## Artwork discovery

Local files searched per ROM, in order, per asset kind (`grid`, `hero`, `logo`, `icon`):

1. `<dir>/<stem>-<kind>.<ext>`
2. `<dir>/media/<kind>/<stem>.<ext>`
3. `<dir>/media/<stem>-<kind>.<ext>`

Extensions tried: `.png`, `.jpg`, `.jpeg`. Max 8 MiB per asset. If not found locally and SGDB is enabled, fetched from `steamgriddb.com`.
