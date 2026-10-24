#!/bin/bash
# Download the Pentair Pool 2025-2026 catalog and render every page to PNG.
# Raw files are not committed (100 MB+); this rebuilds them in a fresh container.
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=data/raw/pentair/pdf
mkdir -p "$DIR/catalog2025" "$DIR/png"
URL="https://www.pentair.com/content/dam/extranet/nam/pentair-pool/residential/catalogs/2025-pool-product-catalog/low-resolution-pdfs-for-posting-2025-2026-edition/pentair-catalog-2025-2026-digital-1-compressed.pdf"
PDF="$DIR/catalog2025/pentair-catalog-2025-2026-digital-1-compressed.pdf"
[ -s "$PDF" ] || curl -sS -m 600 -A "Mozilla/5.0" -o "$PDF" "$URL"
echo "sha256: $(sha256sum "$PDF" | cut -d' ' -f1)"
python3 - "$PDF" "$DIR/png" <<'PY'
import sys, os, pypdfium2 as p
pdf, out = sys.argv[1], sys.argv[2]
d = p.PdfDocument(pdf)
for i in range(len(d)):
    f = os.path.join(out, f"p{i+1:03d}.png")
    if not os.path.exists(f):
        d[i].render(scale=2).to_pil().convert("RGB").save(f, optimize=True)
print("pages:", len(d))
PY
