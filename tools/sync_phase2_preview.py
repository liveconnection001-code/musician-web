from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SEO_ROOT = ROOT / "new_site" / "seo_deployment" / "app" / "webroot"
PREVIEW_ROOTS = (
    ROOT / "temporary_preview_site" / "public",
    ROOT / "new_site" / "preview",
)


def static_guide(source: str) -> str:
    static_meta = """<title>ご依頼の流れ・よくあるご質問｜MUSICIAN 公開前確認</title>
<meta name=\"description\" content=\"MUSICIANのご依頼の流れ・よくあるご質問の公開前確認です。\">
<meta name=\"robots\" content=\"noindex, nofollow, noarchive\">
<link rel=\"canonical\" href=\"https://www.musician.co.jp/guide.html\">"""
    rendered, count = re.subn(
        r"<\?php echo \$this->element\('seo_meta', array\(.*?\)\); \?>",
        static_meta,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("guide.html SEO block was not found exactly once")
    if "<?php" in rendered or "?>" in rendered:
        raise RuntimeError("PHP remained in static guide preview")
    return rendered


def main() -> None:
    guide = static_guide((SEO_ROOT / "guide.html").read_text(encoding="utf-8"))
    for preview_root in PREVIEW_ROOTS:
        (preview_root / "css").mkdir(parents=True, exist_ok=True)
        (preview_root / "guide.html").write_text(guide, encoding="utf-8", newline="\n")
        for name in ("mus_guide.css", "mus_reasons.css"):
            css = (SEO_ROOT / "css" / name).read_text(encoding="utf-8")
            (preview_root / "css" / name).write_text(css, encoding="utf-8", newline="\n")
    print("Phase 2 preview synchronized: guide.html and dedicated CSS")


if __name__ == "__main__":
    main()
