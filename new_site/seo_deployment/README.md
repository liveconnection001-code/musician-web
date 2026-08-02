# MUSICIAN SEO update package

This directory contains the staged, not-yet-uploaded SEO update for the MUSICIAN website.

- Generated from `backup_2026-07-25/site_files`.
- The company template is based on the already-updated achievements template in `new_site/deployment`.
- The backup source files are not modified.
- `seo_manifest.json` records the exact files and hashes intended for deployment.
- Production upload is deliberately excluded until the preview and final checks are approved.

Main changes: canonical URLs, page-specific metadata, Open Graph/Twitter cards, Schema.org JSON-LD, one meaningful H1 per page, heading-hierarchy normalization, a clean sitemap, robots rules, duplicate redirects, true 404 handling, current Instagram/address/footer details, and a six-theme homepage Works section aligned with the Works package.

## Build pipeline

1. `python tools/build_seo_update.py` — regenerates this directory from the backup + the already-deployed company template.
2. `python tools/finalize_seo_update.py` — applies the home LCP-image fix, the company page Schema.org type split (AboutPage vs CollectionPage), updates the company and full-home private previews, and refreshes `seo_manifest.json`.
3. `python tools/validate_seo_update.py` — static validation of the result.

## Next production release

The next approved full production release will use the existing `OBSOLETE_PATHS` quarantine workflow for the 12 superseded gallery files belonging to `traditional-taiko`, `unit-big-band`, and `unit-live-band` (small/card/large variants). Deployment first quarantines these paths; permanent removal is performed only by the existing verified cleanup step after public HTTP checks. No deployment or cleanup is performed as part of this staging update.

`run_build_seo_update.py` and `run_build_seo_update_final.py` were removed on 2026-07-26: their two regex fixes (a legacy `<meta>` matcher that could truncate on an embedded `>`, and a preamble replacement that could raise `re.error: bad escape` on PHP regex literals such as `/\s+/u`) are now part of `build_seo_update.py` itself, so a single script performs the full generation.
