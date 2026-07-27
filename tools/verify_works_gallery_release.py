"""Validate the Works performance gallery before preview or upload."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "new_site" / "works_deployment"
TEMPLATE = DEPLOY / "app/View/catalog/cl01_2/default/index.html"
CSS = DEPLOY / "app/webroot/css/works_showcase.css"
IMAGES = DEPLOY / "app/webroot/images/works/gallery"
MANIFEST = DEPLOY / "performance_gallery_manifest.json"
PREVIEW = ROOT / "temporary_preview_site/app/works/page.tsx"
PREVIEW_IMAGES = ROOT / "temporary_preview_site/public/images/works/gallery"
STAGING_IMAGES = ROOT / "work/release_upload/5_works_gallery/app/webroot/images/works/gallery"
PROCESSOR = ROOT / "tools/prepare_works_performance_gallery.py"
BUILDER = ROOT / "tools/build_works_release.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    preview = PREVIEW.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["photos"]

    keys = [photo["key"] for photo in manifest]
    require(len(keys) == 32, f"Expected 32 photos, found {len(keys)}")
    require(len(set(keys)) == 32, "Gallery keys are not unique")
    template_keys = re.findall(r"array\('image' => '([^']+)'", template)
    preview_keys = re.findall(r'\{ image: "([^"]+)"', preview)
    require(template_keys == keys, "Production gallery keys/order must match the manifest exactly")
    require(preview_keys == keys, "Preview gallery keys/order must match the manifest exactly")
    require("works-performance__lightbox" in template, "In-page gallery enlargement is missing")
    require("works-performance__caption" not in template, "Gallery captions should remain hidden")
    require("'@type' => 'ImageObject'" in template and "'@type' => 'ItemList'" in template, "Image gallery schema is missing")
    require("grid-template-columns: repeat(4" in css, "Desktop four-column gallery layout is missing")
    require("@media (max-width:820px)" in css and "grid-template-columns: repeat(2" in css, "Mobile gallery layout is missing")
    require("object-fit: cover" in css, "Uniform full-bleed 4:3 gallery fitting is missing")
    require("-card.jpg" in template and "-card.jpg" in preview, "Uniform 4:3 gallery previews are missing")
    require("ImageOps.fit(" in PROCESSOR.read_text(encoding="utf-8"), "Full-bleed 4:3 card processing is missing")
    require("$seoDescription = $seoIsRoot" in template, "Root SEO description must not be overwritten by CMS copy")
    require("-large.jpg" in template and "-large.jpg" in preview, "Full gallery images are missing")
    require("IndexIgnore *" in (DEPLOY / "app/webroot/images/works/.htaccess").read_text(encoding="utf-8"), "Safe directory listing protection is missing")
    require("traditional-koto-gala" in PROCESSOR.read_text(encoding="utf-8"), "The event-banner crop configuration is missing")
    require("Refusing to overwrite the curated 32-photo Works gallery" in BUILDER.read_text(encoding="utf-8"), "Legacy Works builder can overwrite the gallery")

    expected_files = []
    for key in keys:
        expected_files.extend((f"{key}-card.jpg", f"{key}-large.jpg"))
    missing = [name for name in expected_files if not (IMAGES / name).is_file()]
    require(not missing, f"Missing gallery derivatives: {missing}")

    total_size = 0
    for name in expected_files:
        path = IMAGES / name
        total_size += path.stat().st_size
        with Image.open(path) as image:
            require(image.width > 0 and image.height > 0, f"Invalid dimensions: {name}")
            require(not image.getexif(), f"EXIF remains: {name}")
            if "-card." in name:
                require(image.size == (960, 720), f"Unexpected card dimensions: {name} {image.size}")
        require(path.stat().st_size <= 1800 * 1024, f"Image exceeds 1.8 MB: {name}")
        production_bytes = path.read_bytes()
        require((PREVIEW_IMAGES / name).read_bytes() == production_bytes, f"Preview image differs: {name}")
        require((STAGING_IMAGES / name).read_bytes() == production_bytes, f"Staging image differs: {name}")

    require(total_size <= 35 * 1024 * 1024, f"Gallery payload is too large: {total_size / 1024 / 1024:.2f} MB")
    print(f"Works gallery validation passed: 32 photos, 64 required JPEG derivatives, {total_size / 1024 / 1024:.2f} MB total")


if __name__ == "__main__":
    main()
