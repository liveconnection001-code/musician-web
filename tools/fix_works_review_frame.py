"""Keep the mobile preview content viewport at the labeled 390 CSS pixels."""

from pathlib import Path


path = Path(__file__).resolve().parents[1] / "temporary_preview_site/app/works-review/review.css"
text = path.read_text(encoding="utf-8")
old = ".device-review__stage--mobile .device-review__frame { border: 9px solid #111; border-radius: 30px; overflow: hidden; }"
new = ".device-review__stage--mobile .device-review__frame { border: 9px solid #111; border-radius: 30px; box-sizing: content-box; overflow: hidden; }"
if old not in text:
    raise RuntimeError("Expected mobile frame rule was not found")
path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
print("Set mobile preview content width to 390 CSS pixels")
