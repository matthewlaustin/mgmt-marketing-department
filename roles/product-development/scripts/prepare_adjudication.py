"""Merge the two blind passes into reviews_final, queueing disagreements for adjudication.

  python3 scripts/prepare_adjudication.py

For every page reviewed in both passes:
- full agreement (same MPN set; same brand, kind, status, replaced_by and normalized title per MPN)
  → pass A's review is copied to reviews_final/pNNN.json (unless a final already exists);
- otherwise → data/work/pentair/adjudicate/pNNN.json lists the differences for a third look.
Existing reviews_final files are never overwritten (adjudicated pages stay adjudicated).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pdfplumber  # noqa: E402

from product_namer.review import normalize_title, page_words, validate  # noqa: E402

PDF = Path(__file__).resolve().parents[1] / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
_pdf = None


def words_for(page: int) -> list[str]:
    global _pdf
    if _pdf is None:
        _pdf = pdfplumber.open(PDF)
    return page_words(_pdf.pages[page - 1])

WORK = Path(__file__).resolve().parents[1] / "data/work/pentair"
FIELDS = ("brand", "kind", "status", "replaced_by", "title")
FORCE_ADJUDICATE = {47}  # p047: pass independence was breached (see rule_issues.md)


def recs(review: dict) -> dict[str, dict]:
    return {r["mpn"]: r for r in review.get("records", [])}


def finished_pages() -> set[int]:
    """Pages whose whole batch has a review in both passes (in-progress batches are skipped)."""
    batches = json.loads((WORK / "batches.json").read_text())["batches"]
    done = set()
    for batch in batches:
        if all((WORK / d / f"p{n:03d}.json").exists() for d in ("reviews", "reviews_b") for n in batch):
            done.update(batch)
    in_batches = {n for b in batches for n in b}
    return done | {n for n in range(1, 541) if n not in in_batches}  # auto-empty pages


def main() -> int:
    ready = finished_pages()
    final_dir, adj_dir = WORK / "reviews_final", WORK / "adjudicate"
    final_dir.mkdir(exist_ok=True)
    adj_dir.mkdir(exist_ok=True)
    agreed = queued = kept = 0
    for a_path in sorted((WORK / "reviews").glob("p*.json")):
        b_path = WORK / "reviews_b" / a_path.name
        if not b_path.exists():
            continue
        page = int(a_path.stem[1:])
        if page not in ready:
            continue
        if (final_dir / a_path.name).exists():
            kept += 1
            continue
        a, b = json.loads(a_path.read_text()), json.loads(b_path.read_text())
        ra, rb = recs(a), recs(b)
        diffs = []
        for mpn in sorted(set(ra) | set(rb)):
            if mpn not in ra or mpn not in rb:
                diffs.append({"mpn": mpn, "only_in": "A" if mpn in ra else "B"})
                continue
            for f in FIELDS:
                va, vb = ra[mpn].get(f) or "", rb[mpn].get(f) or ""
                if f == "title":
                    va, vb = normalize_title(va), normalize_title(vb)
                if va != vb:
                    diffs.append({"mpn": mpn, "field": f, "A": va, "B": vb})
        if a.get("page_type") != b.get("page_type"):
            diffs.append({"field": "page_type", "A": a.get("page_type"), "B": b.get("page_type")})
        if not diffs and validate(a, words_for(page)):
            diffs.append({"field": "validation", "A": "pass A no longer validates (rules/extraction changed)", "B": ""})
        if diffs or page in FORCE_ADJUDICATE:
            (adj_dir / a_path.name).write_text(json.dumps({"page": page, "differences": diffs}, indent=1, ensure_ascii=False))
            queued += 1
        else:
            for r in a.get("records", []):
                r["title"] = normalize_title(r.get("title", ""))
            a["resolution"] = "both passes agree"
            (final_dir / a_path.name).write_text(json.dumps(a, indent=1, ensure_ascii=False))
            (adj_dir / a_path.name).unlink(missing_ok=True)
            agreed += 1
    print(f"agreed → final: {agreed}; queued for adjudication: {queued}; already final: {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
