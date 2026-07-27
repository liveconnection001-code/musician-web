# Works update package

This package changes the Works root page from a dated CMS list to a curated,
theme-based showcase. Existing non-root CMS routes remain intact as an archive.

## Contents

- `app/View/catalog/cl01_2/default/index.html`: CakePHP Works template
- `app/webroot/css/works_showcase.css`: isolated Works styles
- `app/webroot/images/works/`: resized WebP/JPEG photo assets
- `photo_manifest.json`: source-to-output manifest and metadata stripping record

## Photo and logo decision

The selected photos are approved. Prominent client and event logos were
neutralized into their surrounding stage, banner, or booth colors. The
MUSICIAN-logo fallback was not needed because the neutral treatments remained
visually natural. Only the approved `*-clean` variants are included in the
public package. Logo-bearing originals must remain outside every public folder.

## Install

Deploy only the listed files under `app/`. The `images/works` directory contains
only approved `*-clean` images and a protective `.htaccess`; do not upload the
package-level README or manifest files.
The template is based on the current SEO deployment version so its metadata and
structured-data changes are preserved.
The six cases expose stable #work-* anchors that exactly match the six curated
homepage cards in the SEO package. Deploy the Works and SEO packages together so
the homepage links, images, typography, and blue visual system remain aligned.
