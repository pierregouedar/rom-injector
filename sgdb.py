"""SteamGridDB client — stdlib only, disk-cached."""
import base64
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.steamgriddb.com/api/v2"
UA = "rom-injector/0.2 (+https://decky.xyz)"
TIMEOUT = 8.0
MAX_ASSET_BYTES = 4 * 1024 * 1024  # 4 MiB cap per image

# Asset type → (endpoint, query params)
ENDPOINTS = {
    "grid": ("grids",  {"dimensions": "600x900", "types": "static", "nsfw": "false"}),
    "hero": ("heroes", {"types": "static", "nsfw": "false"}),
    "logo": ("logos",  {"types": "static", "nsfw": "false"}),
    "icon": ("icons",  {"types": "static", "nsfw": "false"}),
}


class SgdbError(Exception):
    pass


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "User-Agent": UA}


def _get_json(url: str, api_key: str) -> dict:
    req = urllib.request.Request(url, headers=_headers(api_key))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_bytes(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read(MAX_ASSET_BYTES + 1)
    if len(data) > MAX_ASSET_BYTES:
        raise SgdbError("asset exceeds size cap")
    ct = (r.headers.get("Content-Type") or "").split("/")[-1].split(";")[0].strip().lower()
    ext = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp", "x-icon": "ico", "ico": "ico"}.get(ct, "png")
    return data, ext


def test_key(api_key: str) -> dict:
    if not api_key:
        return {"ok": False, "error": "empty key"}
    try:
        _get_json(f"{API}/search/autocomplete/{urllib.parse.quote('mario')}", api_key)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _clean_name(name: str) -> str:
    # strip common ROM tags: "(USA)", "[!]", "v1.1", region codes
    s = re.sub(r"\([^)]*\)", "", name)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\bv\d+(\.\d+)*\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -_.")
    return s or name


def _cache_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cache_key(name: str, kind: str) -> str:
    h = hashlib.sha1(f"{name}|{kind}".encode()).hexdigest()[:16]
    return f"{h}-{kind}"


def _read_cache(cache_root: Path, key: str) -> dict | None:
    meta = cache_root / f"{key}.json"
    if not meta.exists():
        return None
    try:
        m = json.loads(meta.read_text())
        blob = cache_root / m["file"]
        if not blob.exists():
            return None
        data = blob.read_bytes()
        return {"b64": base64.b64encode(data).decode(), "ext": m["ext"]}
    except Exception:
        return None


def _write_cache(cache_root: Path, key: str, data: bytes, ext: str) -> None:
    _cache_dir(cache_root)
    blob = cache_root / f"{key}.{ext}"
    blob.write_bytes(data)
    (cache_root / f"{key}.json").write_text(json.dumps({"file": blob.name, "ext": ext, "ts": int(time.time())}))


def _write_negative(cache_root: Path, key: str) -> None:
    _cache_dir(cache_root)
    (cache_root / f"{key}.miss").write_text(str(int(time.time())))


def _has_negative(cache_root: Path, key: str, ttl: int = 7 * 24 * 3600) -> bool:
    m = cache_root / f"{key}.miss"
    if not m.exists():
        return False
    try:
        ts = int(m.read_text().strip())
        return (time.time() - ts) < ttl
    except Exception:
        return False


def find_game_id(name: str, api_key: str) -> int | None:
    q = urllib.parse.quote(_clean_name(name))
    data = _get_json(f"{API}/search/autocomplete/{q}", api_key)
    results = data.get("data") or []
    if not results:
        return None
    return results[0].get("id")


def fetch_artwork(
    name: str,
    api_key: str,
    cache_root: Path,
    kinds: tuple[str, ...] = ("grid", "hero", "logo", "icon"),
) -> dict:
    """Return {'grid': {'b64','ext'}, ...} with cache. Missing kinds omitted."""
    out: dict = {}
    if not api_key:
        return out

    # Per-kind cache hits short-circuit without hitting the API.
    needed: list[str] = []
    for kind in kinds:
        ck = _cache_key(name, kind)
        hit = _read_cache(cache_root, ck)
        if hit:
            out[kind] = hit
        elif _has_negative(cache_root, ck):
            continue
        else:
            needed.append(kind)

    if not needed:
        return out

    try:
        gid = find_game_id(name, api_key)
    except Exception:
        return out
    if gid is None:
        for kind in needed:
            _write_negative(cache_root, _cache_key(name, kind))
        return out

    for kind in needed:
        ck = _cache_key(name, kind)
        endpoint, params = ENDPOINTS[kind]
        try:
            url = f"{API}/{endpoint}/game/{gid}?{urllib.parse.urlencode(params)}"
            data = _get_json(url, api_key)
            items = data.get("data") or []
            if not items:
                _write_negative(cache_root, ck)
                continue
            asset_url = items[0].get("url")
            if not asset_url:
                _write_negative(cache_root, ck)
                continue
            bytes_, ext = _get_bytes(asset_url)
            _write_cache(cache_root, ck, bytes_, ext)
            out[kind] = {"b64": base64.b64encode(bytes_).decode(), "ext": ext}
        except Exception:
            _write_negative(cache_root, ck)
            continue

    return out


def clear_cache(cache_root: Path) -> int:
    if not cache_root.exists():
        return 0
    n = 0
    for p in cache_root.iterdir():
        try:
            p.unlink()
            n += 1
        except Exception:
            pass
    return n
