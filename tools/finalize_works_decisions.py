"""Apply final user-approved Works photo and wording decisions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

replacements = {
    ROOT / "temporary_preview_site/app/works/page.tsx": (
        ("箏や尺八などの音色を", "和楽器の音色を"),
        ("箏と尺八を中心とした和楽器演奏のステージ", "和楽器演奏のステージ"),
        (
            "公開前確認用：写真の掲載許可を確認後に本番反映します",
            "公開前確認用：ロゴは現状のまま掲載し、必要に応じて公開前に修正します",
        ),
    ),
    ROOT / "tools/build_works_release.py": (
        ("箏や尺八などの音色を", "和楽器の音色を"),
        ("箏と尺八を中心とした和楽器演奏のステージ", "和楽器演奏のステージ"),
    ),
    ROOT / "new_site/works_deployment/README.md": (
        (
            "The selected photos contain recognizable performers and, in some cases, client\n"
            "or event branding. Confirm the right to publish every photo before uploading\n"
            "this package to production.",
            "Client and event logos are intentionally retained in the selected photos under\n"
            "the current publishing direction. They can be retouched later if needed. Review\n"
            "recognizable performer photos as a separate final-production check.",
        ),
    ),
}

for path, edits in replacements.items():
    text = path.read_text(encoding="utf-8")
    for old, new in edits:
        if old not in text:
            raise RuntimeError(f"Expected text not found in {path}: {old!r}")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Finalized {path.relative_to(ROOT)}")
