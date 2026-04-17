import json
import socket
import urllib.request
from pathlib import Path

import decky

import config as cfg_mod
import logs as logs_mod
import sgdb
from scanner import find_artwork, profiles_index, scan_root, unquote

logs_mod.install()


class Plugin:
    async def _main(self):
        decky.logger.info("rom-injector backend up")

    async def _unload(self):
        decky.logger.info("rom-injector backend down")

    # ── config ──

    async def get_config(self) -> dict:
        return cfg_mod.load()

    async def save_config(self, config: dict) -> dict:
        cleaned = cfg_mod.normalize(config)
        cfg_mod.save(cleaned)
        return cleaned

    async def reset_config(self) -> dict:
        fresh = cfg_mod.defaults()
        cfg_mod.save(fresh)
        return fresh

    # ── import / export ──

    async def export_config(self) -> str:
        return json.dumps(cfg_mod.load(), indent=2)

    async def import_config(self, blob: str) -> dict:
        data = json.loads(blob)
        if not isinstance(data, dict):
            raise ValueError("config root must be object")
        return await self.save_config(data)

    # ── validation ──

    async def validate_config(self) -> dict:
        c = cfg_mod.load()
        return {
            "roots": [{"path": r, "exists": Path(r).is_dir()} for r in c.get("roots", [])],
            "profiles": [
                {"ext": p["ext"], "exe": p["exe"], "exe_exists": Path(p["exe"]).is_file()}
                for p in c.get("profiles", [])
            ],
        }

    # ── scan ──

    async def get_roms_to_sync(self) -> list[dict]:
        c = cfg_mod.load()
        default_compat = c.get("default_compat_tool", "proton_experimental")
        by_ext = profiles_index(c.get("profiles", []))
        sgdb_key = c.get("steamgriddb_api_key") or ""
        sgdb_on = bool(c.get("steamgriddb_enabled")) and bool(sgdb_key)
        cache_root = cfg_mod.sgdb_cache_path()

        out: list[dict] = []
        seen: set[str] = set()
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
                    missing = tuple(k for k in ("grid", "hero", "logo", "icon") if k not in art)
                    if missing:
                        try:
                            fetched = sgdb.fetch_artwork(entry["name"], sgdb_key, cache_root, missing)
                            for k, v in fetched.items():
                                art.setdefault(k, v)
                        except Exception as e:
                            decky.logger.warning(f"sgdb fetch failed for {entry['name']}: {e}")
                entry["artwork"] = art
                out.append(entry)
        decky.logger.info(f"scanned {len(out)} roms across {len(c.get('roots', []))} roots (sgdb={'on' if sgdb_on else 'off'})")
        return out

    # ── SteamGridDB ──

    async def test_steamgriddb_key(self, api_key: str | None = None) -> dict:
        key = (api_key or cfg_mod.load().get("steamgriddb_api_key") or "").strip()
        return sgdb.test_key(key)

    async def clear_sgdb_cache(self) -> int:
        return sgdb.clear_cache(cfg_mod.sgdb_cache_path())

    # ── stale detection ──

    async def find_stale_rom_paths(self, candidate_paths: list[str]) -> list[str]:
        missing: list[str] = []
        for q in candidate_paths:
            raw = unquote(q)
            if raw and not Path(raw).exists():
                missing.append(q)
        return missing

    # ── undo persistence ──

    async def record_last_sync(self, appids: list[int]) -> None:
        cfg_mod.last_sync_path().write_text(json.dumps({"appids": appids}))

    async def get_last_sync(self) -> list[int]:
        p = cfg_mod.last_sync_path()
        if not p.exists():
            return []
        try:
            return list(json.loads(p.read_text()).get("appids") or [])
        except Exception:
            return []

    async def clear_last_sync(self) -> None:
        p = cfg_mod.last_sync_path()
        if p.exists():
            p.unlink()

    # ── logs ──

    async def get_logs(self, limit: int = 100) -> list[str]:
        return logs_mod.tail(limit)

    # ── cef diagnostic ──

    async def check_cef_debugging(self) -> dict:
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
