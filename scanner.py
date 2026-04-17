"""ROM scanner + local artwork discovery."""
import base64
from pathlib import Path

import decky

from config import norm_ext

ICON_EXTS = (".png", ".jpg", ".jpeg", ".ico")
ARTWORK_EXTS = (".png", ".jpg", ".jpeg")
ASSET_TYPES = ("grid", "hero", "logo", "icon")
MAX_ARTWORK_BYTES = 8 * 1024 * 1024


def vdf_quote(s: str) -> str:
    return f'"{s.replace(chr(34), chr(92) + chr(34))}"'


def unquote(s: str) -> str:
    raw = s
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw.replace('\\"', '"')


def find_icon(rom: Path) -> str | None:
    stem = rom.stem
    candidates = [rom.with_suffix(ext) for ext in ICON_EXTS]
    media = rom.parent / "media"
    if media.is_dir():
        candidates += [media / f"{stem}{ext}" for ext in ICON_EXTS]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def find_artwork(rom: Path) -> dict:
    """{'grid': {'b64','ext'}, 'hero':..., 'logo':..., 'icon':...} if found."""
    result: dict = {}
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


def scan_root(root: Path, profiles_by_ext: dict, default_compat: str) -> list[dict]:
    out: list[dict] = []
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


def profiles_index(profiles: list[dict]) -> dict:
    return {norm_ext(p["ext"]): p for p in profiles}
