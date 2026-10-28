"""Layout-aware reading of print catalogs.

Plain text extraction throws away the visual cues a catalog uses to name things: the
big page heading, the subtitle under it, the coloured side tab, the black band that
heads each table section, and side-by-side tables. A row that just says "Lid" only
means something with that context. This module keeps it: every text line comes out
with the stack of headings that govern it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import pdfplumber

# Pentair-style part numbers: 5-8 digits with an optional letter suffix (356363S,
# 354545SS, 6020018Z), letter-prefixed codes (EC-160340, R172187, SP2610X15) and
# Pleatco-style codes (PAP100-4). Deliberately loose: every candidate must be
# confirmed or rejected by the page review, and nothing outside this set can be a SKU.
SKU_TOKEN = re.compile(r"^(?=[A-Z0-9\-./]*\d{3})[A-Z0-9][A-Z0-9\-./]{3,19}$")
PRICE = re.compile(r"^\$?\d{1,3}(,\d{3})*\.\d{2}$")
NOT_SKU = re.compile(
    r"^(\d{1,4}|\d+\.\d+|\d{3}-\d{3}-\d{4}|\d{4}-\d{4}|P/N.*|\d+[x×]\d+|UL\d+|\d{1,3}-\d{1,2})$", re.I
)


@dataclass
class Band:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class Line:
    text: str
    top: float
    x0: float
    x1: float
    bold: bool
    size: float
    band: str = ""  # nearest black section band above this line, in the same column
    table_header: str = ""  # bold column-header line above it, in the same column
    sku_candidates: list[str] = field(default_factory=list)


@dataclass
class PageLayout:
    page: int  # 1-based PDF page index
    printed_page: str  # page number printed on the page, if found
    title: str
    subtitle: str
    side_tab: str
    notes: list[str]  # e.g. "Replacement Parts for Product #348190", "SEE PAGE 427 ..."
    bands: list[Band]
    lines: list[Line]

    def to_dict(self) -> dict:
        return asdict(self)

    def sku_candidates(self) -> list[str]:
        seen: dict[str, None] = {}
        for line in self.lines:
            for sku in line.sku_candidates:
                seen.setdefault(sku)
        return list(seen)


def _is_black_fill(rect: dict) -> bool:
    color = rect.get("non_stroking_color")
    if not isinstance(color, (list, tuple)):
        return False
    if len(color) == 4:  # CMYK
        return color[3] >= 0.9 and max(color[:3]) <= 0.2
    if len(color) == 3:
        return max(color) <= 0.15
    if len(color) == 1:
        return color[0] <= 0.15
    return False


def _clean(text: str) -> str:
    text = text.replace("®", "®").replace("™", "™")
    return re.sub(r"\s+", " ", text).strip()


def _join_words(words: list[dict]) -> str:
    words = sorted(words, key=lambda w: w["x0"])
    out = ""
    prev = None
    for w in words:
        if prev is not None and w["x0"] - prev["x1"] > 1.0:
            out += " "
        out += w["text"]
        prev = w
    return _clean(out)


def _group_lines(words: list[dict], tolerance: float = 2.5) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        for line in lines:
            if abs(line[0]["top"] - w["top"]) <= tolerance:
                line.append(w)
                break
        else:
            lines.append([w])
    return sorted(lines, key=lambda ln: ln[0]["top"])


def _split_columns(line: list[dict], bands: list[Band], gap: float = 18.0) -> list[list[dict]]:
    """Split a visual line into pieces that belong to different side-by-side tables."""
    line = sorted(line, key=lambda w: w["x0"])
    pieces: list[list[dict]] = [[line[0]]]
    for w in line[1:]:
        prev = pieces[-1][-1]
        crosses_band_edge = any(prev["x1"] <= b.x1 + 1 < w["x0"] for b in bands)
        if w["x0"] - prev["x1"] > gap and crosses_band_edge:
            pieces.append([w])
        else:
            pieces[-1].append(w)
    return pieces


def sku_candidates(text: str) -> list[str]:
    found = []
    for raw in text.replace(",", " ").split():
        tok = raw.strip("()[]:;*†‡•°").upper()
        if PRICE.match(tok) or NOT_SKU.match(tok):
            continue
        if SKU_TOKEN.match(tok):
            found.append(tok)
    return found


def read_page(page: pdfplumber.page.Page, page_number: int) -> PageLayout:
    words = page.extract_words(
        extra_attrs=["fontname", "size", "upright"], keep_blank_chars=False, use_text_flow=False
    )
    width, height = page.width, page.height

    # The side tab is rotated text in the outer margin.
    tab_chars = [c for c in page.chars if not c.get("upright", True) and (c["x0"] > width - 60 or c["x1"] < 60)]
    side_tab = _clean("".join(c["text"] for c in sorted(tab_chars, key=lambda c: -c["top"] if c["x0"] < 60 else c["top"])))

    upright = [w for w in words if w.get("upright", True)]
    big = [w for w in upright if w["top"] < 90 and w["size"] >= 14]
    big_tops = {round(w["top"]) for w in big}
    # keep the small ® / ™ marks that sit on the heading lines
    top_words = big + [w for w in upright if w["top"] < 90 and w["size"] < 14 and round(w["top"]) in big_tops and w["text"] in "®™"]
    title = _join_words([w for w in top_words if "Bold" in w["fontname"]])
    subtitle = _join_words([w for w in top_words if "Bold" not in w["fontname"]])

    bands = []
    for r in page.rects:
        h = r["bottom"] - r["top"]
        if _is_black_fill(r) and 6 <= h <= 30 and (r["x1"] - r["x0"]) > 80:
            inside = [w for w in upright if r["x0"] - 1 <= w["x0"] and w["x1"] <= r["x1"] + 1 and r["top"] - 1 <= w["top"] and w["bottom"] <= r["bottom"] + 1]
            if inside:
                bands.append(Band(_join_words(inside), r["x0"], r["x1"], r["top"], r["bottom"]))
    bands.sort(key=lambda b: (b.top, b.x0))
    band_word_ids = {
        id(w) for b in bands for w in upright
        if b.x0 - 1 <= w["x0"] and w["x1"] <= b.x1 + 1 and b.top - 1 <= w["top"] and w["bottom"] <= b.bottom + 1
    }

    body = [w for w in upright if id(w) not in band_word_ids and w not in top_words]
    printed_page = ""
    lines: list[Line] = []
    notes: list[str] = []
    headers: list[Line] = []
    for visual_line in _group_lines(body):
        for piece in _split_columns(visual_line, bands):
            text = _join_words(piece)
            if not text:
                continue
            x0 = min(w["x0"] for w in piece)
            x1 = max(w["x1"] for w in piece)
            top = min(w["top"] for w in piece)
            bold = all("Bold" in w["fontname"] or "Black" in w["fontname"] for w in piece)
            size = max(w["size"] for w in piece)
            if re.fullmatch(r"\d{1,3}", text) and top > height - 60 and bold:
                printed_page = text
                continue
            if re.search(r"Replacement Parts for|SEE PAGE|See page|Refer to (catalog )?page", text, re.I):
                notes.append(text)
            line = Line(text=text, top=top, x0=x0, x1=x1, bold=bold, size=round(size, 1))
            if bold and size <= 8 and re.search(r"\b(Part|Product|Item|Description|Model)\b", text):
                headers.append(line)
            lines.append(line)

    def in_column(x0: float, x1: float, b_x0: float, b_x1: float) -> bool:
        return x0 >= b_x0 - 4 and x1 <= b_x1 + 4

    for line in lines:
        above = [b for b in bands if b.bottom <= line.top + 1 and in_column(line.x0, line.x1, b.x0, b.x1)]
        if above:
            line.band = max(above, key=lambda b: b.top).text
        hdr = [h for h in headers if h.top < line.top and h is not line and h.x0 <= line.x1 and h.x1 >= line.x0]
        if hdr:
            line.table_header = max(hdr, key=lambda h: h.top).text
        if not line.bold:
            line.sku_candidates = sku_candidates(line.text)

    return PageLayout(
        page=page_number,
        printed_page=printed_page,
        title=title,
        subtitle=subtitle,
        side_tab=side_tab,
        notes=notes,
        bands=bands,
        lines=lines,
    )


def read_pdf(path: str, pages: list[int] | None = None):
    """Yield a PageLayout for each requested 1-based page (all pages if None)."""
    with pdfplumber.open(path) as pdf:
        numbers = pages or range(1, len(pdf.pages) + 1)
        for n in numbers:
            yield read_page(pdf.pages[n - 1], n)


def page_text_tokens(path: str, page_number: int) -> set[str]:
    """Every SKU-shaped token in the page's text layer: the ground truth for audits."""
    with pdfplumber.open(path) as pdf:
        text = pdf.pages[page_number - 1].extract_text() or ""
    return set(sku_candidates(text))
