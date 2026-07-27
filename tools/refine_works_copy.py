"""Apply the final fact-safe wording refinement to Works source files."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "temporary_preview_site/app/works/page.tsx",
    ROOT / "tools/build_works_release.py",
)
REPLACEMENTS = (
    ("箏や尺八などの音色を", "和楽器の音色を"),
    ("箏と尺八を中心とした和楽器演奏のステージ", "和楽器演奏のステージ"),
)


for path in FILES:
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Refined {path.relative_to(ROOT)}")
