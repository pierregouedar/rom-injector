"""Config schema, load/save/migrate."""
import json
from pathlib import Path

import decky

CONFIG_NAME = "config.json"
LAST_SYNC_NAME = "last_sync.json"
SGDB_CACHE_DIR = "sgdb_cache"
VALID_LANGS = {"en", "fr", "de", "it", "es", "nl"}

DEFAULT_CONFIG = {
    "roots": ["/home/deck/Emulation/roms"],
    "default_compat_tool": "proton_experimental",
    "assign_collection": "ROMs",
    "steamgriddb_api_key": "",
    "steamgriddb_enabled": False,
    "profiles": [
        {"ext": ".gba",  "exe": "/usr/bin/flatpak", "args": "run io.mgba.mGBA {rom}",                                                             "compat_tool": ""},
        {"ext": ".gb",   "exe": "/usr/bin/flatpak", "args": "run io.mgba.mGBA {rom}",                                                             "compat_tool": ""},
        {"ext": ".gbc",  "exe": "/usr/bin/flatpak", "args": "run io.mgba.mGBA {rom}",                                                             "compat_tool": ""},
        {"ext": ".nes",  "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/fceumm_libretro.so {rom}",           "compat_tool": ""},
        {"ext": ".snes", "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/snes9x_libretro.so {rom}",           "compat_tool": ""},
        {"ext": ".smc",  "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/snes9x_libretro.so {rom}",           "compat_tool": ""},
        {"ext": ".sfc",  "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/snes9x_libretro.so {rom}",           "compat_tool": ""},
        {"ext": ".n64",  "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/mupen64plus_next_libretro.so {rom}", "compat_tool": ""},
        {"ext": ".z64",  "exe": "/usr/bin/flatpak", "args": "run org.libretro.RetroArch -L /app/lib/libretro/mupen64plus_next_libretro.so {rom}", "compat_tool": ""},
    ],
}


def settings_dir() -> Path:
    return Path(decky.DECKY_PLUGIN_SETTINGS_DIR)


def config_path() -> Path:
    return settings_dir() / CONFIG_NAME


def last_sync_path() -> Path:
    return settings_dir() / LAST_SYNC_NAME


def sgdb_cache_path() -> Path:
    return settings_dir() / SGDB_CACHE_DIR


def norm_ext(ext: str) -> str:
    ext = (ext or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    return ext


def migrate(cfg: dict) -> dict:
    if "roots" not in cfg:
        legacy_root = cfg.get("root")
        cfg["roots"] = [legacy_root] if legacy_root else list(DEFAULT_CONFIG["roots"])
    cfg.setdefault("default_compat_tool", cfg.pop("compat_tool", "proton_experimental"))
    cfg.setdefault("assign_collection", DEFAULT_CONFIG["assign_collection"])
    cfg.setdefault("steamgriddb_api_key", "")
    cfg.setdefault("steamgriddb_enabled", False)
    cfg.setdefault("profiles", list(DEFAULT_CONFIG["profiles"]))
    cfg.pop("root", None)
    return cfg


def load() -> dict:
    p = config_path()
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        return migrate(json.loads(p.read_text()))
    except Exception as e:
        decky.logger.warning(f"bad config, defaulting: {e}")
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save(cfg: dict) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))


def normalize(incoming: dict) -> dict:
    """Clean + validate user-submitted config (from save_config RPC)."""
    cfg = migrate(dict(incoming))
    cfg["roots"] = [r.strip() for r in (cfg.get("roots") or []) if isinstance(r, str) and r.strip()]
    cleaned: list[dict] = []
    for p in cfg.get("profiles") or []:
        ext = norm_ext(p.get("ext", ""))
        exe = (p.get("exe") or "").strip()
        args = (p.get("args") or "").strip() or "{rom}"
        if not ext or not exe:
            continue
        cleaned.append({
            "ext": ext, "exe": exe, "args": args,
            "compat_tool": (p.get("compat_tool") or "").strip(),
        })
    cfg["profiles"] = cleaned
    cfg["default_compat_tool"] = (cfg.get("default_compat_tool") or "proton_experimental").strip()
    cfg["assign_collection"] = (cfg.get("assign_collection") or "").strip()
    cfg["steamgriddb_api_key"] = (cfg.get("steamgriddb_api_key") or "").strip()
    cfg["steamgriddb_enabled"] = bool(cfg.get("steamgriddb_enabled", False))
    lang = (cfg.get("language") or "").strip().lower()
    if lang in VALID_LANGS:
        cfg["language"] = lang
    else:
        cfg.pop("language", None)
    return cfg


def defaults() -> dict:
    return json.loads(json.dumps(DEFAULT_CONFIG))
