"""Pick one photo per SKU from data/work/photos/candidates.json (scripts/photo_candidates.py).

  python3 scripts/photo_select.py download   # fetch the qualifying candidate images (cached, ~2 per second)
  python3 scripts/photo_select.py choose     # data/work/photos/chosen.json

Rules (Matthew 2026-10-26): Pentair's own photo when it is 1000 x 1000 or larger; otherwise the best outside
image: at least 1000 x 1000, preferring one that several independent sites show (same picture by perceptual
hash), then Pool Geek's own store, then resolution. A store image that the same store also uses for 3+ other
part numbers is a placeholder (logo, generic line photo) and is dropped. Watermarks are checked afterwards by
eye (scripts/photo_review.py), and a rejected photo falls back to the next candidate.
"""

from __future__ import annotations

import collections
import hashlib
import io
import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data/work/photos/candidates.json"
CACHE = ROOT / "data/raw/photos"
HASHES = ROOT / "data/work/photos/hashes.json"
CHOSEN = ROOT / "data/work/photos/chosen.json"
REJECT = ROOT / "data/work/photos/rejected.json"  # image_url -> reason, from the visual review
UA = "Mozilla/5.0 (compatible; PoolGeekCatalogBot/0.1; +https://poolgeek.com)"
SITE_PREF = {"www.poolgeek.com": 0}
# whole stores whose photos all carry a watermark (found by eye, 2026-10-26)
EXCLUDE_SOURCES = {"www.bathandspaparts.com": "every photo carries a watermark (water-drop logo and '(c) Bath & Spa Parts Online')"}


def cache_path(url: str) -> Path:
    ext = Path(url.split("?")[0]).suffix.lower()
    ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ".img"
    return CACHE / f"{hashlib.sha1(url.encode()).hexdigest()[:16]}{ext}"


def dhash(im: Image.Image) -> int:
    """64-bit difference hash on a white-flattened greyscale copy."""
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        im = bg
    g = im.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.tobytes())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (px[r * 9 + c] > px[r * 9 + c + 1])
    return bits


def ham(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def wanted(cands: dict) -> list[str]:
    urls = []
    for m, r in cands.items():
        if not r["needs_outside"]:
            continue
        for c in r["stores"] + r["manufacturer"]:
            if c.get("image_url") and c.get("grade") in ("ok", "long") and not c.get("file"):
                urls.append(c["image_url"])
    return sorted(set(urls))


def download(shard: int = 0, shards: int = 1) -> int:
    """Shards run as separate processes (the proxy adds seconds per request); each writes its own hash file,
    merged by merge()."""
    cands = json.loads(CAND.read_text())
    hashes = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    CACHE.mkdir(parents=True, exist_ok=True)
    urls = [u for i, u in enumerate(u for u in wanted(cands) if u not in hashes) if i % shards == shard]
    out_file = HASHES if shards == 1 else HASHES.with_name(f"hashes.part{shard}.json")
    part = json.loads(out_file.read_text()) if shards > 1 and out_file.exists() else {}
    urls = [u for u in urls if u not in part]
    hashes = hashes if shards == 1 else part
    print(len(urls), "to fetch", flush=True)
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for i, u in enumerate(urls, 1):
        p = cache_path(u)
        try:
            if not p.exists():
                time.sleep(0.25)
                r = s.get(u, timeout=30)
                if r.status_code != 200:
                    hashes[u] = {"error": r.status_code}
                    continue
                p.write_bytes(r.content)
            with Image.open(p) as im:
                hashes[u] = {"file": str(p.relative_to(ROOT)), "width": im.width, "height": im.height, "dhash": dhash(im), "bytes": p.stat().st_size}
        except Exception as e:  # noqa: BLE001
            hashes[u] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        if i % 25 == 0:
            out_file.write_text(json.dumps(hashes))
            print(f"  {i} fetched", flush=True)
    out_file.write_text(json.dumps(hashes))
    print(len([h for h in hashes.values() if "dhash" in h]), "images hashed")
    return 0


def choose() -> int:
    cands = json.loads(CAND.read_text())
    hashes = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    rejected = json.loads(REJECT.read_text()) if REJECT.exists() else {}
    # placeholders: one store image used for 3+ different part numbers on that store
    per_site = collections.defaultdict(lambda: collections.defaultdict(set))
    for m, r in cands.items():
        for c in r["stores"]:
            h = hashes.get(c.get("image_url") or "", {}).get("dhash")
            if h is not None:
                per_site[c["source"]][h].add(m)
    placeholder = {(site, h) for site, d in per_site.items() for h, ms in d.items() if len(ms) >= 4}
    wf = ROOT / "data/work/photos/web_candidates.json"  # scripts/page_images.py: pages found by web search
    web = {k: v for k, v in json.loads(wf.read_text()).items() if k != "_checked"} if wf.exists() else {}
    out, why = {}, collections.Counter()
    for m, r in sorted(cands.items()):
        if not r["needs_outside"]:
            best = max((c for c in r["manufacturer"] if c["grade"] == "ok"), key=lambda c: (c["match"] == "sku", c["label"] == "product", c["width"] * c["height"]))
            out[m] = dict(best, tier="manufacturer", sites=["pentair.com"])
            why["manufacturer"] += 1
            continue
        pool = []
        for c in r["stores"] + web.get(m, []) + [c for c in r["manufacturer"] if c["grade"] in ("ok", "long")]:
            h = hashes.get(c.get("image_url") or "")
            if not h or "dhash" not in h or c["image_url"] in rejected or c["source"] in EXCLUDE_SOURCES:
                continue
            if (c["source"], h["dhash"]) in placeholder:
                why["placeholder dropped"] += 1
                continue
            g = "ok" if min(h["width"], h["height"]) >= 1000 else "long" if max(h["width"], h["height"]) >= 1000 else "small"
            if g == "small":
                continue
            pool.append(dict(c, width=h["width"], height=h["height"], grade=g, dhash=h["dhash"], file=c.get("file") or h["file"]))
        if not pool:
            continue
        for c in pool:  # independent sites showing the same picture
            c["sites"] = sorted({d["source"] for d in pool if ham(d["dhash"], c["dhash"]) <= 6})
        best = min(pool, key=lambda c: (c["grade"] != "ok", c["source"] != "pentair.com", -len(c["sites"]), SITE_PREF.get(c["source"], 1), -(c["width"] * c["height"])))
        best = {k: v for k, v in best.items() if k != "dhash"}
        best["tier"] = ("pentair (long side)" if best["source"] == "pentair.com" else
                        "multi-site" if len(best["sites"]) >= 2 else "pool geek" if best["source"] == "www.poolgeek.com" else "single site")
        if best["grade"] != "ok":
            best["tier"] += ", below 1000x1000"
        out[m] = best
        why[best["tier"]] += 1
    CHOSEN.write_text(json.dumps(out, indent=1))
    need = sum(1 for r in cands.values() if r["needs_outside"])
    print(f"{len(out)} of {len(cands)} SKUs have a photo; outside photos for {len(out) - why['manufacturer']} of {need} that needed one")
    for k, v in why.most_common():
        print(f"  {k:34} {v}")
    print(f"  {len(placeholder)} placeholder images found across stores")
    return 0


def merge() -> int:
    hashes = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    for f in sorted(HASHES.parent.glob("hashes.part*.json")):
        hashes.update(json.loads(f.read_text()))
    HASHES.write_text(json.dumps(hashes))
    for f in HASHES.parent.glob("hashes.part*.json"):
        f.unlink()
    print(len(hashes), "image hashes")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "download":
        raise SystemExit(download(*(int(x) for x in sys.argv[2:4])))
    raise SystemExit({"choose": choose, "merge": merge}[cmd]())
