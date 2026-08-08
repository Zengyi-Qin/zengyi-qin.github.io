#!/usr/bin/env python3
"""Build the static GitHub Pages entrypoint from the editable source files."""

from pathlib import Path


ROOT = Path(__file__).parent
SOURCE = ROOT / "src"
OUTPUT = ROOT / "index.html"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    sections = sorted((SOURCE / "sections").glob("*.html"))
    if not sections:
        raise SystemExit("No section files found in src/sections.")

    parts = [read(SOURCE / "templates" / "head.html")]
    parts.extend(read(section) for section in sections)
    parts.append(read(SOURCE / "templates" / "footer.html"))
    OUTPUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Built {OUTPUT.relative_to(ROOT)} from {len(sections)} sections.")


if __name__ == "__main__":
    main()
