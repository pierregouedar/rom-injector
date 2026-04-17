"""ROM Injector — single-file backend.

Kept deliberately monolithic: some Decky Loader versions don't add the plugin
directory to sys.path reliably, which breaks sibling imports like
'from scanner import ...'. One file dodges the whole problem.
"""

import base64
import hashlib
import json
import logging
import re
import socket
import time
import traceback
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

import decky

# ─── constants ───────────────────────────────────────────────────────────
CONFIG_NAME = "config.json"
LAST_SYNC_NAME = "last_sync.json"
SGDB_CACHE_DIR = "sgdb_cache"
ICON_EXTS = (".png", ".jpg", ".jpeg", ".ico")
ARTWORK_EXTS = (".png", ".jpg", ".jpeg")
ASSET_TYPES = ("grid", "hero", "logo", "icon")
MAX_ARTWORK_BYTES = 8 * 1024 * 1024
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


# ─── log ring buffer ─────────────────────────────────────────────────────
LOG_BUFFER = deque(maxlen=500)


class _RingHandler(logging.Handler):
    def emit(self, record):
        try:
            LOG_BUFFER.append(f"{record.levelname:<7} {record.getMessage()}")
        except Exception:
            pass


try:
    _h = _RingHandler()
    _h.setLevel(logging.INFO)
    decky.logger.addHandler(_h)
except Exception:
    pass


# ─── path helpers ────────────────────────────────────────────────────────
def settings_dir():
    return Path(decky.DECKY_PLUGIN_SETTINGS_DIR)


def config_path():
    return settings_dir() / CONFIG_NAME


def last_sync_path():
    return settings_dir() / LAST_SYNC_NAME


def sgdb_cache_path():
    return settings_dir() / SGDB_CACHE_DIR


def norm_ext(ext):
    ext = (ext or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    return ext


def vdf_quote(s):
    return '"' + s.replace('"', '\\"') + '"'


def unquote(s):
    raw = s
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw.replace('\\"', '"')


# ─── config IO ───────────────────────────────────────────────────────────
def cfg_migrate(cfg):
    if "roots" not in cfg:
        legacy = cfg.get("root")
        cfg["roots"] = [legacy] if legacy else list(DEFAULT_CONFIG["roots"])
    cfg.setdefault("default_compat_tool", cfg.pop("compat_tool", "proton_experimental"))
    cfg.setdefault("assign_collection", DEFAULT_CONFIG["assign_collection"])
    cfg.setdefault("steamgriddb_api_key", "")
    cfg.setdefault("steamgriddb_enabled", False)
    cfg.setdefault("profiles", list(DEFAULT_CONFIG["profiles"]))
    cfg.pop("root", None)
    return cfg


def cfg_load():
    p = config_path()
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        return cfg_migrate(json.loads(p.read_text()))
    except Exception as e:
        decky.logger.warning(f"bad config, defaulting: {e}")
        return json.loads(json.dumps(DEFAULT_CONFIG))


def cfg_save(cfg):
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))


def cfg_normalize(incoming):
    """Sanitize whitespace but keep every user-entered row verbatim.

    Empty roots/profiles are preserved so the UI can autosave while the user
    is mid-typing. Filtering happens at scan time, not at save time.
    """
    cfg = cfg_migrate(dict(incoming))
    cfg["roots"] = [str(r).strip() for r in (cfg.get("roots") or []) if isinstance(r, str)]
    cleaned = []
    for p in cfg.get("profiles") or []:
        cleaned.append({
            "ext": norm_ext(p.get("ext", "")),
            "exe": (p.get("exe") or "").strip(),
            "args": (p.get("args") or "").strip() or "{rom}",
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


# ─── scanner ─────────────────────────────────────────────────────────────
def find_icon(rom):
    stem = rom.stem
    candidates = [rom.with_suffix(ext) for ext in ICON_EXTS]
    media = rom.parent / "media"
    if media.is_dir():
        candidates += [media / f"{stem}{ext}" for ext in ICON_EXTS]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def find_artwork(rom):
    result = {}
    parent = rom.parent
    stem = rom.stem
    for key in ASSET_TYPES:
        for ext in ARTWORK_EXTS:
            paths = [
                parent / f"{stem}-{key}{ext}",
                parent / "media" / key / f"{stem}{ext}",
                parent / "media" / f"{stem}-{key}{ext}",
            ]
            chosen = next((p for p in paths if p.is_file()), None)
            if not chosen:
                continue
            try:
                data = chosen.read_bytes()
                if len(data) > MAX_ARTWORK_BYTES:
                    decky.logger.warning(f"artwork too large, skipping: {chosen}")
                    break
                result[key] = {
                    "b64": base64.b64encode(data).decode(),
                    "ext": ext.lstrip("."),
                }
            except Exception as e:
                decky.logger.warning(f"artwork read failed {chosen}: {e}")
            break
    return result


def scan_root(root, profiles_by_ext, default_compat):
    out = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        profile = profiles_by_ext.get(path.suffix.lower())
        if not profile:
            continue
        launch_opts = profile["args"].format(rom=vdf_quote(str(path)))
        out.append({
            "name":        path.stem,
            "exe":         vdf_quote(profile["exe"]),
            "start_dir":   vdf_quote(str(path.parent)),
            "launch_opts": launch_opts,
            "icon_path":   find_icon(path) or "",
            "compat_tool": profile.get("compat_tool") or default_compat,
            "dedupe_key":  f"{profile['exe']}|{launch_opts}",
            "rom_path":    str(path),
        })
    return out


# ─── SteamGridDB (inlined) ───────────────────────────────────────────────
SGDB_API = "https://www.steamgriddb.com/api/v2"
SGDB_UA = "rom-injector/0.2 (+https://decky.xyz)"
SGDB_TIMEOUT = 8.0
SGDB_MAX_BYTES = 4 * 1024 * 1024
SGDB_ENDPOINTS = {
    "grid": ("grids",  {"dimensions": "600x900", "types": "static", "nsfw": "false"}),
    "hero": ("heroes", {"types": "static", "nsfw": "false"}),
    "logo": ("logos",  {"types": "static", "nsfw": "false"}),
    "icon": ("icons",  {"types": "static", "nsfw": "false"}),
}


def _sgdb_headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "User-Agent": SGDB_UA}


def _sgdb_get_json(url, api_key):
    req = urllib.request.Request(url, headers=_sgdb_headers(api_key))
    with urllib.request.urlopen(req, timeout=SGDB_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _sgdb_get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": SGDB_UA})
    with urllib.request.urlopen(req, timeout=SGDB_TIMEOUT) as r:
        data = r.read(SGDB_MAX_BYTES + 1)
    if len(data) > SGDB_MAX_BYTES:
        raise RuntimeError("asset exceeds size cap")
    ct = (r.headers.get("Content-Type") or "").split("/")[-1].split(";")[0].strip().lower()
    ext = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp", "x-icon": "ico", "ico": "ico"}.get(ct, "png")
    return data, ext


def _sgdb_clean_name(name):
    s = re.sub(r"\([^)]*\)", "", name)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\bv\d+(\.\d+)*\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -_.")
    return s or name


def _sgdb_cache_key(name, kind):
    h = hashlib.sha1(f"{name}|{kind}".encode()).hexdigest()[:16]
    return f"{h}-{kind}"


def _sgdb_read_cache(root, key):
    meta = root / f"{key}.json"
    if not meta.exists():
        return None
    try:
        m = json.loads(meta.read_text())
        blob = root / m["file"]
        if not blob.exists():
            return None
        data = blob.read_bytes()
        return {"b64": base64.b64encode(data).decode(), "ext": m["ext"]}
    except Exception:
        return None


def _sgdb_write_cache(root, key, data, ext):
    root.mkdir(parents=True, exist_ok=True)
    blob = root / f"{key}.{ext}"
    blob.write_bytes(data)
    (root / f"{key}.json").write_text(json.dumps({"file": blob.name, "ext": ext, "ts": int(time.time())}))


def _sgdb_write_miss(root, key):
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{key}.miss").write_text(str(int(time.time())))


def _sgdb_has_miss(root, key, ttl=7 * 24 * 3600):
    m = root / f"{key}.miss"
    if not m.exists():
        return False
    try:
        ts = int(m.read_text().strip())
        return (time.time() - ts) < ttl
    except Exception:
        return False


def sgdb_test_key(api_key):
    if not api_key:
        return {"ok": False, "error": "empty key"}
    try:
        _sgdb_get_json(f"{SGDB_API}/search/autocomplete/{urllib.parse.quote('mario')}", api_key)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sgdb_clear_cache(root):
    if not root.exists():
        return 0
    n = 0
    for p in root.iterdir():
        try:
            p.unlink()
            n += 1
        except Exception:
            pass
    return n


def sgdb_fetch_artwork(name, api_key, cache_root, kinds):
    out = {}
    if not api_key:
        return out
    needed = []
    for kind in kinds:
        ck = _sgdb_cache_key(name, kind)
        hit = _sgdb_read_cache(cache_root, ck)
        if hit:
            out[kind] = hit
        elif _sgdb_has_miss(cache_root, ck):
            continue
        else:
            needed.append(kind)
    if not needed:
        return out
    try:
        q = urllib.parse.quote(_sgdb_clean_name(name))
        data = _sgdb_get_json(f"{SGDB_API}/search/autocomplete/{q}", api_key)
        results = data.get("data") or []
        gid = results[0].get("id") if results else None
    except Exception:
        return out
    if gid is None:
        for kind in needed:
            _sgdb_write_miss(cache_root, _sgdb_cache_key(name, kind))
        return out
    for kind in needed:
        ck = _sgdb_cache_key(name, kind)
        endpoint, params = SGDB_ENDPOINTS[kind]
        try:
            url = f"{SGDB_API}/{endpoint}/game/{gid}?{urllib.parse.urlencode(params)}"
            d = _sgdb_get_json(url, api_key)
            items = d.get("data") or []
            if not items:
                _sgdb_write_miss(cache_root, ck)
                continue
            asset_url = items[0].get("url")
            if not asset_url:
                _sgdb_write_miss(cache_root, ck)
                continue
            bytes_, ext = _sgdb_get_bytes(asset_url)
            _sgdb_write_cache(cache_root, ck, bytes_, ext)
            out[kind] = {"b64": base64.b64encode(bytes_).decode(), "ext": ext}
        except Exception:
            _sgdb_write_miss(cache_root, ck)
            continue
    return out


# ─── Plugin class ────────────────────────────────────────────────────────
class Plugin:
    async def _main(self):
        decky.logger.info("rom-injector backend up (single-file)")

    async def _unload(self):
        decky.logger.info("rom-injector backend down")

    async def ping(self):
        """Sanity-check endpoint — returns immediately if backend is alive."""
        return {"ok": True, "plugin": "rom-injector"}

    # ── config ──
    async def get_config(self):
        try:
            return cfg_load()
        except Exception as e:
            decky.logger.error(f"get_config failed: {e}\n{traceback.format_exc()}")
            raise

    async def save_config(self, config):
        cleaned = cfg_normalize(config)
        try:
            cfg_save(cleaned)
        except Exception as e:
            decky.logger.error(f"save_config write failed at {config_path()}: {e}\n{traceback.format_exc()}")
            raise
        decky.logger.info(f"save_config wrote {config_path()} ({config_path().stat().st_size} bytes)")
        return cleaned

    async def debug_paths(self):
        """Diagnostic: settings dir + writability probe."""
        cp = config_path()
        settings = settings_dir()
        info = {
            "settings_dir": str(settings),
            "settings_exists": settings.exists(),
            "config_path": str(cp),
            "config_exists": cp.exists(),
            "config_size": cp.stat().st_size if cp.exists() else None,
        }
        # Try a probe write
        probe = settings / ".rom-injector-probe"
        try:
            settings.mkdir(parents=True, exist_ok=True)
            probe.write_text(str(int(time.time())))
            info["probe_write"] = "ok"
            probe.unlink()
        except Exception as e:
            info["probe_write"] = f"FAILED: {type(e).__name__}: {e}"
        return info

    async def reset_config(self):
        fresh = json.loads(json.dumps(DEFAULT_CONFIG))
        cfg_save(fresh)
        return fresh

    async def export_config(self):
        return json.dumps(cfg_load(), indent=2)

    async def import_config(self, blob):
        data = json.loads(blob)
        if not isinstance(data, dict):
            raise ValueError("config root must be object")
        return await self.save_config(data)

    async def validate_config(self):
        c = cfg_load()
        return {
            "roots": [{"path": r, "exists": Path(r).is_dir()} for r in c.get("roots", [])],
            "profiles": [
                {"ext": p["ext"], "exe": p["exe"], "exe_exists": Path(p["exe"]).is_file()}
                for p in c.get("profiles", [])
            ],
        }

    # ── scan ──
    async def get_roms_to_sync(self):
        c = cfg_load()
        default_compat = c.get("default_compat_tool", "proton_experimental")
        # Filter out empty/partial profiles at scan time (saved verbatim, used selectively).
        by_ext = {
            norm_ext(p["ext"]): p
            for p in c.get("profiles", [])
            if p.get("ext") and p.get("exe")
        }
        sgdb_key = c.get("steamgriddb_api_key") or ""
        sgdb_on = bool(c.get("steamgriddb_enabled")) and bool(sgdb_key)
        cache_root = sgdb_cache_path()

        out = []
        seen = set()
        for root in c.get("roots", []):
            path = Path(root)
            if not path.is_dir():
                decky.logger.warning(f"root missing: {path}")
                continue
            for entry in scan_root(path, by_ext, default_compat):
                if entry["dedupe_key"] in seen:
                    continue
                seen.add(entry["dedupe_key"])
                art = find_artwork(Path(entry["rom_path"]))
                if sgdb_on:
                    missing = tuple(k for k in ASSET_TYPES if k not in art)
                    if missing:
                        try:
                            fetched = sgdb_fetch_artwork(entry["name"], sgdb_key, cache_root, missing)
                            for k, v in fetched.items():
                                art.setdefault(k, v)
                        except Exception as e:
                            decky.logger.warning(f"sgdb fetch failed for {entry['name']}: {e}")
                entry["artwork"] = art
                out.append(entry)
        decky.logger.info(f"scanned {len(out)} roms across {len(c.get('roots', []))} roots (sgdb={'on' if sgdb_on else 'off'})")
        return out

    # ── SteamGridDB ──
    async def test_steamgriddb_key(self, api_key=None):
        key = (api_key or cfg_load().get("steamgriddb_api_key") or "").strip()
        return sgdb_test_key(key)

    async def clear_sgdb_cache(self):
        return sgdb_clear_cache(sgdb_cache_path())

    # ── stale ──
    async def find_stale_rom_paths(self, candidate_paths):
        missing = []
        for q in candidate_paths:
            raw = unquote(q)
            if raw and not Path(raw).exists():
                missing.append(q)
        return missing

    # ── undo ──
    async def record_last_sync(self, appids):
        last_sync_path().write_text(json.dumps({"appids": appids}))

    async def get_last_sync(self):
        p = last_sync_path()
        if not p.exists():
            return []
        try:
            return list(json.loads(p.read_text()).get("appids") or [])
        except Exception:
            return []

    async def clear_last_sync(self):
        p = last_sync_path()
        if p.exists():
            p.unlink()

    # ── logs ──
    async def get_logs(self, limit=100):
        n = max(1, min(limit, len(LOG_BUFFER)))
        return list(LOG_BUFFER)[-n:]

    # ── CEF diag ──
    async def check_cef_debugging(self):
        try:
            with socket.create_connection(("127.0.0.1", 8080), timeout=0.5):
                pass
        except OSError as e:
            return {"ok": False, "error": str(e)}
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/json", timeout=1.0) as r:
                targets = json.load(r)
            has_shared = any(t.get("title") == "SharedJSContext" for t in targets)
            return {
                "ok": has_shared,
                "targets": len(targets),
                "note": "" if has_shared else "port open but SharedJSContext missing",
            }
        except Exception as e:
            return {"ok": False, "error": f"HTTP probe failed: {e}"}
