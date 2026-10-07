#!/usr/bin/env bash
# Rebuild docs/ from the local WordPress preview for GitHub Pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! curl -fsS -o /dev/null --max-time 10 http://localhost:8080/; then
  echo "The local preview is not running. Start it with ./bin/preview.sh and run this again." >&2
  exit 1
fi

python3 "$ROOT/scripts/export_static.py"

python3 - << 'PY'
from pathlib import Path
root = Path("docs")
checks = {
    "home": root / "index.html",
    "meetings": root / "general-meetings" / "index.html",
    "join": root / "join-the-pi" / "index.html",
    "sigs": root / "special-interest-groups" / "index.html",
    "board": root / "the-pi-board" / "index.html",
    "blog": root / "blog" / "index.html",
    "contact": root / "contact-us" / "index.html",
}
failed = False
for name, path in checks.items():
    if not path.is_file():
        print(f"missing {name}: {path}")
        failed = True
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    images = text.count("/Apple-Pi-Wordpress/wp-content/uploads/") + text.count("/Apple-Pi-Wordpress/wp-content/themes/")
    banner = "not the official site" in text
    print(f"{name}: images~{images} banner={banner}")
    if images < 1 or not banner:
        failed = True
contact = (root / "contact-us" / "index.html").read_text(encoding="utf-8", errors="replace")
if "This form does not send email." not in contact:
    print("contact form notice missing")
    failed = True
localhost_hits = []
for path in root.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".html", ".css", ".js", ".svg"}:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    if "localhost" in text or "127.0.0.1" in text:
        localhost_hits.append(str(path))
if localhost_hits:
    print("localhost still present:")
    for hit in localhost_hits[:20]:
        print(" ", hit)
    failed = True
if failed:
    raise SystemExit(1)
print("export checks passed")
PY
