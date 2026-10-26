"""Upload the downloaded media (product photos, manuals and brochures, diagram and chart renders) to the
Cloudflare R2 bucket, and record each object's key so the images / documents tables can carry it.

  python3 scripts/r2_upload.py --dry-run     # what would go up: counts and sizes, no credentials needed
  python3 scripts/r2_upload.py               # upload what is not up yet (idempotent)

Credentials come from the environment (never from the repo or the chat): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET and, when the bucket has a public domain, R2_PUBLIC_URL (e.g.
https://media.poolgeek.com). Matthew chose R2 on the 2026-10-26 diagram review.

Keys: pentair/photos/<file>, pentair/docs/<file>, pentair/diagrams/<file>, pentair/charts/<file>, where
<file> is the local file name (already hashed from the source URL, so a re-download of the same URL maps to
the same key). The map local_file -> {key, url, bytes} is written to data/work/pentair/r2_objects.json.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/catalog.db"
MAP = ROOT / "data/work/pentair/r2_objects.json"
PREFIX = {"main": "photos", "gallery": "photos", "marketing": "photos", "diagram": "diagrams", "chart": "charts"}


def plan(con: sqlite3.Connection) -> list[tuple[str, str]]:
    """(local_file, key) for every file on disk that a table row points to."""
    out = []
    for local, role in con.execute("SELECT DISTINCT local_file, role FROM images WHERE local_file IS NOT NULL"):
        out.append((local, f"pentair/{PREFIX.get(role, 'photos')}/{Path(local).name}"))
    for (local,) in con.execute("SELECT DISTINCT local_file FROM documents WHERE local_file IS NOT NULL"):
        out.append((local, f"pentair/docs/{Path(local).name}"))
    return [(l, k) for l, k in out if (ROOT / l).exists()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(DB)
    todo = plan(con)
    done = json.loads(MAP.read_text()) if MAP.exists() else {}
    by_prefix: dict[str, list[int]] = {}
    for local, key in todo:
        by_prefix.setdefault(key.split("/")[1], []).append((ROOT / local).stat().st_size)
    for p, sizes in sorted(by_prefix.items()):
        print(f"  {p:9} {len(sizes):5} files {sum(sizes) / 1e6:8.1f} MB")
    print(f"{len(todo)} files, {sum(s for v in by_prefix.values() for s in v) / 1e9:.2f} GB; {sum(1 for l, _ in todo if l in done)} already uploaded")
    if args.dry_run:
        return 0
    missing = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET") if not os.environ.get(k)]
    if missing:
        print("not set in the environment:", ", ".join(missing), file=sys.stderr)
        return 2
    import boto3  # installed on demand; not needed for the dry run

    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    bucket, public = os.environ["R2_BUCKET"], os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    n = 0
    for local, key in todo:
        if local in done:
            continue
        path = ROOT / local
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": ctype, "CacheControl": "public, max-age=31536000, immutable"})
        done[local] = {"key": key, "url": f"{public}/{key}" if public else None, "bytes": path.stat().st_size}
        n += 1
        if n % 50 == 0:
            MAP.write_text(json.dumps(done, indent=1))
            print(f"  {n} uploaded")
    MAP.write_text(json.dumps(done, indent=1))
    print(f"{n} uploaded; {len(done)} objects recorded in {MAP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
