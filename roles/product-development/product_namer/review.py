"""Page packets for review, and the checks every page review must pass.

A page review (done by reading the rendered page image alongside its text layer)
produces records plus an explicit list of dismissed tokens. The checks here make two
guarantees that do not depend on the reviewer being careful:

1. Precision: every MPN exists, character for character, in the page's text layer.
2. Completeness: every SKU-shaped token on the page is either a record or dismissed
   with a reason.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

from .pdf_layout import read_page

SPEC = re.compile(
    r"^\d+(\.\d+)?(V|W|HP|THP|GPM|GPH|FT|IN|MM|CM|LBS?|PSI|BTU|BTUH|K|A|AMPS?|HZ|RPM|°F?|'|′|\")$",
    re.I,
)
PRICE = re.compile(r"^\$?\d{1,3}(,\d{3})*\.\d{2}$")
YEARS = re.compile(r"^(19|20)\d{2}(-(19|20)?\d{2}|-CURRENT)?$", re.I)
# "3-Way", "2-Speed", "1st", "2nd": wording, not part numbers
WORDY = re.compile(r"^(\d{1,2}-[A-Z]?[a-z]+|\d+(st|nd|rd|th))$")
TRAILING_MARKS = "*¹²³⁴⁵†‡•°,;:()[]"

DISMISS_REASONS = {
    "cross_reference",  # another company's part number (Mfr #, Unicel, Filbur, OEM, competitor)
    "spec_value",  # dimension, rating, voltage, model year, etc.
    "page_reference",  # catalog page or figure reference
    "document_code",  # Prop 65 label P/N, form numbers, patent numbers, standards (UL1081)
    "model_name",  # a model/series name that is not a sellable SKU on this page
    "other",  # explain in note
}

STATUSES = {"active", "discontinued", "not_for_sale_usa"}
KINDS = {"whole_good", "accessory", "part"}
BRANDS = {"Pentair", "Sta-Rite", "Pleatco"}

BANNED_IN_TITLE = [
    (re.compile(r"\(Qty\.?", re.I), "assembly quantity left in title"),
    (re.compile(r"Includes Items|Items? \d", re.I), "diagram item reference left in title"),
    (re.compile(r"CONT[’']?D", re.I), "(CONT'D) left in title"),
    (re.compile(r"\(|\)"), "parenthesis left in title"),
    (re.compile(r"\s{2,}"), "double space"),
    (re.compile(r"[.,;:\-]$"), "trailing punctuation"),
    (re.compile(r"\b(in|ft)\.(\s|$)"), "unit with period (use 'in', 'ft')"),
]


def normalize_token(raw: str) -> str:
    return raw.strip(TRAILING_MARKS).strip()


def is_candidate(tok: str) -> bool:
    """SKU-shaped: a digit plus a letter (len>=3), or 5+ digits. Excludes obvious non-SKUs."""
    if len(tok) < 3 or len(tok) > 24:
        return False
    if PRICE.match(tok) or SPEC.match(tok) or YEARS.match(tok) or WORDY.match(tok):
        return False
    if re.fullmatch(r"[\d.,/\-x×]+", tok):  # numbers, ranges, fractions, dimensions
        return len(re.sub(r"\D", "", tok)) >= 5 and re.fullmatch(r"\d{5,9}[A-Z]{0,3}", tok) is not None
    has_digit = any(c.isdigit() for c in tok)
    has_alpha = any(c.isalpha() for c in tok)
    return has_digit and has_alpha and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-./]*", tok) is not None


def page_words(page: pdfplumber.page.Page) -> list[str]:
    return [w["text"] for w in page.extract_words(keep_blank_chars=False)]


def page_tokens(words: list[str]) -> tuple[set[str], set[str]]:
    """(all normalized tokens on the page, SKU-shaped candidate tokens)."""
    all_tokens: set[str] = set()
    for w in words:
        for part in re.split(r"[\s,]+", w):
            t = normalize_token(part)
            if t:
                all_tokens.add(t)
    return all_tokens, {t for t in all_tokens if is_candidate(t)}


def build_packet(pdf_path: str, page_number: int, png_dir: str) -> dict:
    """Everything a reviewer needs for one page."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]
        layout = read_page(page, page_number)
        words = page_words(page)
    _, candidates = page_tokens(words)
    return {
        "page": page_number,
        "printed_page": layout.printed_page or str(page_number - 2),
        "image": str(Path(png_dir) / f"p{page_number:03d}.png"),
        "heading": layout.title,
        "subtitle": layout.subtitle,
        "side_tab": layout.side_tab,
        "notes": layout.notes,
        "bands": [b.text for b in layout.bands],
        "lines": [
            {"band": ln.band, "text": ln.text, "bold": ln.bold}
            for ln in layout.lines
            if not re.fullmatch(r"[\d\s]+", ln.text)  # drop exploded-diagram callout numbers
        ],
        "candidate_tokens": sorted(candidates),
    }


def validate(review: dict, words: list[str]) -> list[str]:
    """Return a list of problems; empty means the review passes."""
    errors: list[str] = []
    all_tokens, candidates = page_tokens(words)
    seen: set[str] = set()
    for i, rec in enumerate(review.get("records", [])):
        where = f"record {i} ({rec.get('mpn')})"
        mpn = rec.get("mpn", "")
        if not mpn:
            errors.append(f"{where}: missing mpn")
            continue
        if mpn not in all_tokens:
            errors.append(f"{where}: MPN not found verbatim in page text layer")
        if mpn in seen:
            errors.append(f"{where}: duplicate MPN on page")
        seen.add(mpn)
        brand = rec.get("brand")
        if brand not in BRANDS:
            errors.append(f"{where}: brand {brand!r} not in {sorted(BRANDS)}")
        title = rec.get("title", "")
        prefix = f"{brand} {mpn} - "
        if not title.startswith(prefix):
            errors.append(f"{where}: title must start with {prefix!r}")
        derived = title[len(prefix):] if title.startswith(prefix) else title
        if not derived.strip():
            errors.append(f"{where}: empty derived title")
        for pattern, message in BANNED_IN_TITLE:
            if pattern.search(derived):
                errors.append(f"{where}: {message}: {derived!r}")
        if rec.get("status", "active") not in STATUSES:
            errors.append(f"{where}: bad status {rec.get('status')!r}")
        if rec.get("kind") not in KINDS:
            errors.append(f"{where}: bad kind {rec.get('kind')!r}")
        replaced_by = rec.get("replaced_by")
        if replaced_by and replaced_by not in all_tokens:
            errors.append(f"{where}: replaced_by {replaced_by!r} not on page")

    dismissed = {}
    for d in review.get("dismissed", []):
        tok = d.get("token", "")
        if d.get("reason") not in DISMISS_REASONS:
            errors.append(f"dismissed {tok!r}: reason must be one of {sorted(DISMISS_REASONS)}")
        if d.get("reason") == "other" and not d.get("note"):
            errors.append(f"dismissed {tok!r}: reason 'other' needs a note")
        dismissed[tok] = d
    overlap = seen & set(dismissed)
    for tok in sorted(overlap):
        errors.append(f"token {tok!r} is both a record and dismissed")
    unaccounted = candidates - seen - set(dismissed)
    for tok in sorted(unaccounted):
        errors.append(f"unaccounted SKU-shaped token {tok!r}: add a record or dismiss it with a reason")
    return errors


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
