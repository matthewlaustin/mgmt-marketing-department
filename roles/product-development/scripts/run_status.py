"""Show progress of the two blind review passes over the catalog.

  python3 scripts/run_status.py            # summary + next batches to launch
  python3 scripts/run_status.py --failing  # list pages whose review fails validation

A batch is done for a pass when every page in it has a review that validates.
State lives only in the review files, so this is safe to run from a fresh session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_namer.review import load_json, page_words, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work/pentair"
PDF = ROOT / "data/raw/pentair/pdf/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
PASSES = ("reviews", "reviews_b")


def main() -> int:
    batches = json.loads((WORK / "batches.json").read_text())["batches"]
    status: dict[str, list[str]] = {}
    failing = []
    with pdfplumber.open(PDF) as pdf:
        words_cache: dict[int, list[str]] = {}
        for pass_dir in PASSES:
            states = []
            for batch in batches:
                state = "done"
                for n in batch:
                    path = WORK / pass_dir / f"p{n:03d}.json"
                    if not path.exists():
                        state = "todo" if state == "todo" or n == batch[0] else "partial"
                        continue
                    if n not in words_cache:
                        words_cache[n] = page_words(pdf.pages[n - 1])
                    if validate(load_json(path), words_cache[n]):
                        failing.append(f"{pass_dir}/p{n:03d}")
                        state = "partial"
                if state == "done" and not all((WORK / pass_dir / f"p{n:03d}.json").exists() for n in batch):
                    state = "partial"
                states.append(state)
            status[pass_dir] = states
    for pass_dir, states in status.items():
        print(f"{pass_dir}: {states.count('done')}/{len(states)} batches done, "
              f"{states.count('partial')} partial, {states.count('todo')} todo")
        todo = [i for i, s in enumerate(states) if s != "done"]
        print(f"  not done: {todo}")
    if "--failing" in sys.argv:
        print("failing pages:", failing or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
