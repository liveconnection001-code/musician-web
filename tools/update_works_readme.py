"""Record the approved logo-retention decision in the Works handoff notes."""

from pathlib import Path


path = Path(__file__).resolve().parents[1] / "new_site/works_deployment/README.md"
text = path.read_text(encoding="utf-8")
old = (
    "The selected photos are approved. Prominent client and event logos were\n"
    "neutralized into their surrounding stage, banner, or booth colors. The\n"
    "MUSICIAN-logo fallback was not needed because the neutral treatments remained\n"
    "visually natural. Only the approved `*-clean` variants are included in the\n"
    "public package. Logo-bearing originals must remain outside every public folder."
)
new = old
if old not in text:
    raise RuntimeError("Expected publishing-gate wording was not found")
path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
print("Updated new_site/works_deployment/README.md")
