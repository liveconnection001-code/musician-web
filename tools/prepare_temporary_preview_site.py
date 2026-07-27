#!/usr/bin/env python3
"""Prepare the private hosted preview from the validated static company page."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "temporary_preview_site"
SOURCE = ROOT / "new_site" / "preview"
PUBLIC = PROJECT / "public"


def replace_asset_urls(source: str) -> str:
    replacements = {
        "https://www.musician.co.jp/css/": "css/",
        "https://www.musician.co.jp/js/": "js/",
        "https://www.musician.co.jp/images/": "images/",
        "https://www.musician.co.jp/favicon.png": "favicon.png",
        "https://www.musician.co.jp/apple-touch-icon.png": "apple-touch-icon.png",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    project_resolved = PROJECT.resolve()
    if project_resolved != (ROOT / "temporary_preview_site").resolve():
        raise RuntimeError("Unexpected preview project path")

    PUBLIC.mkdir(parents=True, exist_ok=True)
    for folder in ("css", "images", "js"):
        src = SOURCE / folder
        dst = PUBLIC / folder
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    for filename in ("favicon.png", "apple-touch-icon.png"):
        src = SOURCE / filename
        if src.exists():
            shutil.copy2(src, PUBLIC / filename)

    company_html = (SOURCE / "company.html").read_text(encoding="utf-8")
    company_html = replace_asset_urls(company_html)
    write_text(PUBLIC / "company.html", company_html)

    write_text(
        PROJECT / "app" / "page.tsx",
        '''import type { Metadata } from "next";\n\nexport const metadata: Metadata = {\n  title: "MUSICIAN 実績ページ｜公開前確認",\n  description: "MUSICIAN実績ページの公開前確認用サイトです。",\n};\n\nexport default function Home() {\n  return (\n    <main className="preview-gate">\n      <div className="preview-gate__card">\n        <p className="preview-gate__eyebrow">Private Preview</p>\n        <h1>MUSICIAN 実績ページ</h1>\n        <p>2019〜2026年の実績を追加した、公開前の確認用ページです。</p>\n        <a href="/achievements.html">実績ページを開く</a>\n      </div>\n    </main>\n  );\n}\n''',
    )

    write_text(
        PROJECT / "app" / "layout.tsx",
        '''import type { Metadata } from "next";\nimport "./globals.css";\n\nexport const metadata: Metadata = {\n  title: "MUSICIAN 実績ページ｜公開前確認",\n  description: "MUSICIAN実績ページの公開前確認用サイトです。",\n  robots: { index: false, follow: false },\n  icons: { icon: "/favicon.png" },\n};\n\nexport default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {\n  return (\n    <html lang="ja">\n      <body>{children}</body>\n    </html>\n  );\n}\n''',
    )

    write_text(
        PROJECT / "app" / "globals.css",
        '''@import "tailwindcss";\n\n:root {\n  --navy: #041e42;\n  --orange: #e36927;\n  --beige: #fbe1bd;\n}\n\n* { box-sizing: border-box; }\n\nhtml, body { margin: 0; min-height: 100%; }\n\nbody {\n  background: #f6f4ef;\n  color: var(--navy);\n  font-family: "Yu Mincho", "Hiragino Mincho ProN", serif;\n}\n\n.preview-gate {\n  align-items: center;\n  display: flex;\n  justify-content: center;\n  min-height: 100vh;\n  padding: 32px 20px;\n}\n\n.preview-gate__card {\n  background: #fff;\n  border-left: 6px solid var(--orange);\n  box-shadow: 0 20px 60px rgba(4, 30, 66, .12);\n  max-width: 680px;\n  padding: 44px;\n  width: 100%;\n}\n\n.preview-gate__eyebrow {\n  color: var(--orange);\n  font-family: Arial, sans-serif;\n  font-size: 12px;\n  font-weight: 700;\n  letter-spacing: .16em;\n  margin: 0 0 10px;\n  text-transform: uppercase;\n}\n\n.preview-gate h1 { font-size: clamp(28px, 5vw, 42px); margin: 0 0 18px; }\n.preview-gate p { line-height: 1.9; }\n.preview-gate a {\n  background: var(--navy);\n  color: #fff;\n  display: inline-block;\n  margin-top: 18px;\n  padding: 14px 24px;\n  text-decoration: none;\n}\n.preview-gate a:hover, .preview-gate a:focus-visible { background: var(--orange); }\n''',
    )

    starter_preview = PROJECT / "app" / "_sites-preview"
    if starter_preview.exists():
        shutil.rmtree(starter_preview)

    package_path = PROJECT / "package.json"
    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    package_data["name"] = "musician-achievements-private-preview"
    package_data["scripts"]["dev"] = "vinext dev"
    package_data["scripts"]["build"] = "vinext build"
    package_data["scripts"]["start"] = "vinext start"
    package_data["dependencies"].pop("react-loading-skeleton", None)
    write_text(package_path, json.dumps(package_data, ensure_ascii=False, indent=2) + "\n")

    print(f"Prepared {PUBLIC / 'company.html'}")


if __name__ == "__main__":
    main()
