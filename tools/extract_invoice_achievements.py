from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pdfplumber


EXCLUDED_PARTS = (
    "支払請求書",
    "支払い請求書",
    "支払調書",
    "経費清算",
    "領収書",
)

STOP_DETAIL_WORDS = ("小計", "消費税", "合計", "内訳", "備考", "振込", "お支払")
SENSITIVE_WORDS = (
    "銀行",
    "支店",
    "口座",
    "登録番号",
    "〒",
    "住所",
    "tel",
    "fax",
    "電話",
    "メール",
    "@",
)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u3000", " ")).strip()


def safe_public_line(value: str) -> str:
    line = normalize(value)
    if not line or any(word in line.lower() for word in SENSITIVE_WORDS):
        return ""
    line = re.sub(r"[￥¥]\s*\d[\d,]*(?:\.\d+)?", "", line)
    line = re.sub(r"(?<![\d/-])\d{1,3}(?:,\d{3})+(?:円)?", "", line)
    line = re.sub(r"\b\d{7,}\b", "", line)
    line = re.sub(r"\s+", " ", line).strip(" -・")
    return line


def filename_date(name: str) -> str | None:
    patterns = (
        r"(?<!\d)(20\d{2})[_-](\d{1,2})[_-](\d{1,2})(?!\d)",
        r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)",
        r"(?<!\d)(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日",
    )
    for pattern in patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        try:
            return datetime(*map(int, match.groups())).date().isoformat()
        except ValueError:
            continue
    return None


def text_date(lines: list[str]) -> str | None:
    prioritized = [line for line in lines if "請求日" in line]
    for line in prioritized + lines[:15]:
        match = re.search(r"(20\d{2})[-/.年]\s*(\d{1,2})[-/.月]\s*(\d{1,2})日?", line)
        if not match:
            continue
        try:
            return datetime(*map(int, match.groups())).date().isoformat()
        except ValueError:
            continue
    return None


def extract_client(lines: list[str]) -> str:
    for line in lines[:20]:
        if "御中" not in line and not line.endswith("様"):
            continue
        if "株式会社MUSICIAN" in line or "株式会社東京アーティスト協会" in line:
            continue
        value = re.split(r"御中|\s様(?:\s|$)", line, maxsplit=1)[0]
        value = re.sub(r"^(?:請求書|御請求書)\s*", "", value)
        value = safe_public_line(value)
        if value:
            return value
    return ""


def extract_subject(lines: list[str]) -> str:
    for line in lines:
        match = re.search(r"件\s*名\s*[:：]?\s*(.+)$", line)
        if match:
            return safe_public_line(match.group(1))
    return ""


def extract_invoice_number(lines: list[str]) -> str:
    for line in lines[:20]:
        match = re.search(r"(?:請求書番号|No\.?)[\s：:]*(\d{4,})", line, re.I)
        if match:
            return match.group(1)
    return ""


def extract_details(lines: list[str], subject: str) -> list[str]:
    start = None
    for index, line in enumerate(lines):
        if "摘要" in line or "品 目 名" in line or "品目名" in line:
            start = index + 1
            break
    if start is None:
        return []
    details: list[str] = []
    for line in lines[start : start + 25]:
        if any(word in line for word in STOP_DETAIL_WORDS):
            break
        value = safe_public_line(line)
        value = re.sub(r"(?:^|\s)\d+(?:\.\d+)?\s*$", "", value).strip()
        if not value or value == subject or value in details:
            continue
        details.append(value)
    return details[:8]


def read_pdf(path: Path) -> tuple[list[str], str | None]:
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((page.extract_text(x_tolerance=2, y_tolerance=3) or "") for page in pdf.pages[:2])
        return [normalize(line) for line in text.splitlines() if normalize(line)], None
    except Exception as exc:  # keep the batch moving and report the file
        return [], f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--from-year", type=int, default=2019)
    args = parser.parse_args()
    if len(args.root) != len(args.source):
        parser.error("--root and --source counts must match")

    records: list[dict[str, object]] = []
    skipped = Counter()
    for raw_root, source in zip(args.root, args.source, strict=True):
        root = Path(raw_root)
        for path in sorted(root.rglob("*.pdf"), key=lambda item: str(item).lower()):
            if any(part in str(path) for part in EXCLUDED_PARTS):
                skipped["excluded_payment_or_receipt"] += 1
                continue
            lines, error = read_pdf(path)
            date = filename_date(path.name) or text_date(lines)
            if date and int(date[:4]) < args.from_year:
                skipped["before_start_year"] += 1
                continue
            subject = extract_subject(lines)
            records.append(
                {
                    "source": source,
                    "source_file": path.name,
                    "relative_path": str(path.relative_to(root)),
                    "invoice_date": date,
                    "year": int(date[:4]) if date else None,
                    "client": extract_client(lines),
                    "subject": subject,
                    "details": extract_details(lines, subject),
                    "invoice_number": extract_invoice_number(lines),
                    "text_extracted": bool(lines),
                    "error": error,
                }
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "from_year": args.from_year,
        "record_count": len(records),
        "skipped": dict(skipped),
        "records": records,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "record_count": len(records),
        "with_subject": sum(bool(row["subject"]) for row in records),
        "with_client": sum(bool(row["client"]) for row in records),
        "with_details": sum(bool(row["details"]) for row in records),
        "text_failures": sum(not row["text_extracted"] for row in records),
        "errors": sum(bool(row["error"]) for row in records),
        "years": dict(sorted(Counter(str(row["year"]) for row in records).items())),
        "skipped": dict(skipped),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
